"""
Health check and failover management
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from .base import ProviderType, ProviderHealth, ProviderStatus
from .providers.base import OutlookProvider


logger = logging.getLogger(__name__)


class HealthChecker:
    """
    Health Check Manager
    Track the health status of each provider and manage failover
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        disable_duration: int = 300,
        recovery_check_interval: int = 60,
    ):
        """
        Initialize health checker

        Args:
            failure_threshold: Threshold for the number of consecutive failures, disabled after exceeding
            disable_duration: disable duration (seconds)
            recovery_check_interval: Recovery check interval (seconds)
        """
        self.failure_threshold = failure_threshold
        self.disable_duration = disable_duration
        self.recovery_check_interval = recovery_check_interval

        # Provider health status: ProviderType -> ProviderHealth
        self._health_status: Dict[ProviderType, ProviderHealth] = {}
        self._lock = threading.Lock()

        # Initialize the health status of all providers
        for provider_type in ProviderType:
            self._health_status[provider_type] = ProviderHealth(
                provider_type=provider_type
            )

    def get_health(self, provider_type: ProviderType) -> ProviderHealth:
        """Get the provider's health status"""
        with self._lock:
            return self._health_status.get(provider_type, ProviderHealth(provider_type=provider_type))

    def record_success(self, provider_type: ProviderType):
        """Record successful operations"""
        with self._lock:
            health = self._health_status.get(provider_type)
            if health:
                health.record_success()
                logger.debug(f"{provider_type.value} recorded successfully")

    def record_failure(self, provider_type: ProviderType, error: str):
        """Record failed operations"""
        with self._lock:
            health = self._health_status.get(provider_type)
            if health:
                health.record_failure(error)

                # Check if it needs to be disabled
                if health.should_disable(self.failure_threshold):
                    health.disable(self.disable_duration)
                    logger.warning(
                        f"{provider_type.value} has been disabled for {self.disable_duration} seconds,"
                        f"Reason: {error}"
                    )

    def is_available(self, provider_type: ProviderType) -> bool:
        """
        Check if the provider is available

        Args:
            provider_type: provider type

        Returns:
            Is it available
        """
        health = self.get_health(provider_type)

        # Check if disabled
        if health.is_disabled():
            remaining = (health.disabled_until - datetime.now()).total_seconds()
            logger.debug(
                f"{provider_type.value} has been disabled with {int(remaining)} seconds remaining"
            )
            return False

        return health.status != ProviderStatus.DISABLED

    def get_available_providers(
        self,
        priority_order: Optional[List[ProviderType]] = None,
    ) -> List[ProviderType]:
        """
        Get a list of available providers

        Args:
            priority_order: priority order, default is [IMAP_NEW, IMAP_OLD, GRAPH_API]

        Returns:
            List of available providers
        """
        if priority_order is None:
            priority_order = [
                ProviderType.IMAP_NEW,
                ProviderType.IMAP_OLD,
                ProviderType.GRAPH_API,
            ]

        available = []
        for provider_type in priority_order:
            if self.is_available(provider_type):
                available.append(provider_type)

        return available

    def get_next_available_provider(
        self,
        priority_order: Optional[List[ProviderType]] = None,
    ) -> Optional[ProviderType]:
        """
        Get the next available provider

        Args:
            priority_order: priority order

        Returns:
            Available provider types, or None if none
        """
        available = self.get_available_providers(priority_order)
        return available[0] if available else None

    def force_disable(self, provider_type: ProviderType, duration: Optional[int] = None):
        """
        Force disabling of provider

        Args:
            provider_type: provider type
            duration: Disable duration (seconds), the configured value is used by default
        """
        with self._lock:
            health = self._health_status.get(provider_type)
            if health:
                health.disable(duration or self.disable_duration)
                logger.warning(f"{provider_type.value} has been forcibly disabled")

    def force_enable(self, provider_type: ProviderType):
        """
        Force provider to be enabled

        Args:
            provider_type: provider type
        """
        with self._lock:
            health = self._health_status.get(provider_type)
            if health:
                health.enable()
                logger.info(f"{provider_type.value} is enabled")

    def get_all_health_status(self) -> Dict[str, Any]:
        """
        Get the health status of all providers

        Returns:
            health status dictionary
        """
        with self._lock:
            return {
                provider_type.value: health.to_dict()
                for provider_type, health in self._health_status.items()
            }

    def check_and_recover(self):
        """
        Check and restore disabled providers

        Automatically resume provider if disabled time has elapsed
        """
        with self._lock:
            for provider_type, health in self._health_status.items():
                if health.is_disabled():
                    # Check if it can be restored
                    if health.disabled_until and datetime.now() >= health.disabled_until:
                        health.enable()
                        logger.info(f"{provider_type.value} has been automatically restored")

    def reset_all(self):
        """Reset the health status of all providers"""
        with self._lock:
            for provider_type in ProviderType:
                self._health_status[provider_type] = ProviderHealth(
                    provider_type=provider_type
                )
            logger.info("Health status of all providers has been reset")


class FailoverManager:
    """
    failover manager
    Manage automatic switching between providers
    """

    def __init__(
        self,
        health_checker: HealthChecker,
        priority_order: Optional[List[ProviderType]] = None,
    ):
        """
        Initialize the failover manager

        Args:
            health_checker: health checker
            priority_order: provider priority order
        """
        self.health_checker = health_checker
        self.priority_order = priority_order or [
            ProviderType.IMAP_NEW,
            ProviderType.IMAP_OLD,
            ProviderType.GRAPH_API,
        ]

        # Currently used provider index
        self._current_index = 0
        self._lock = threading.Lock()

    def get_current_provider(self) -> Optional[ProviderType]:
        """
        Get current provider

        Returns:
            The current provider type, or None if no one is available
        """
        available = self.health_checker.get_available_providers(self.priority_order)
        if not available:
            return None

        with self._lock:
            # Try to use the current index
            if self._current_index < len(available):
                return available[self._current_index]
            return available[0]

    def switch_to_next(self) -> Optional[ProviderType]:
        """
        Switch to next provider

        Returns:
            Next provider type, returns None if none are available
        """
        available = self.health_checker.get_available_providers(self.priority_order)
        if not available:
            return None

        with self._lock:
            self._current_index = (self._current_index + 1) % len(available)
            next_provider = available[self._current_index]
            logger.info(f"Switch to provider: {next_provider.value}")
            return next_provider

    def on_provider_success(self, provider_type: ProviderType):
        """
        Called when the provider is successful

        Args:
            provider_type: provider type
        """
        self.health_checker.record_success(provider_type)

        # Reset index to successful provider
        with self._lock:
            available = self.health_checker.get_available_providers(self.priority_order)
            if provider_type in available:
                self._current_index = available.index(provider_type)

    def on_provider_failure(self, provider_type: ProviderType, error: str):
        """
        Called when the provider fails

        Args:
            provider_type: provider type
            error: error message
        """
        self.health_checker.record_failure(provider_type, error)

    def get_status(self) -> Dict[str, Any]:
        """
        Get failover status

        Returns:
            status dictionary
        """
        current = self.get_current_provider()
        return {
            "current_provider": current.value if current else None,
            "priority_order": [p.value for p in self.priority_order],
            "available_providers": [
                p.value for p in self.health_checker.get_available_providers(self.priority_order)
            ],
            "health_status": self.health_checker.get_all_health_status(),
        }
