"""Outlook provider abstract base class"""

import abc
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from ..base import ProviderType, EmailMessage, ProviderHealth, ProviderStatus
from ..account import OutlookAccount


logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Provider configuration"""
    timeout: int = 30
    max_retries: int = 3
    proxy_url: Optional[str] = None

    # Health check configuration
    health_failure_threshold: int = 3
    health_disable_duration: int = 300  # Seconds


class OutlookProvider(abc.ABC):
    """Outlook provider abstract base class
    Define the abstract methods all providers must implement"""

    def __init__(
        self,
        account: OutlookAccount,
        config: Optional[ProviderConfig] = None,
    ):
        """Initialize the provider

        Args:
            account: Outlook account
            config: provider configuration"""
        self.account = account
        self.config = config or ProviderConfig()

        # health status
        self._health = ProviderHealth(provider_type=self.provider_type)

        # connection status
        self._connected = False
        self._last_error: Optional[str] = None

    @property
    @abc.abstractmethod
    def provider_type(self) -> ProviderType:
        """Get provider type"""
        pass

    @property
    def health(self) -> ProviderHealth:
        """Get health status"""
        return self._health

    @property
    def is_healthy(self) -> bool:
        """True if the provider is healthy"""
        return (
            self._health.status == ProviderStatus.HEALTHY
            and not self._health.is_disabled()
        )

    @property
    def is_connected(self) -> bool:
        """True if the provider is connected"""
        return self._connected

    @abc.abstractmethod
    def connect(self) -> bool:
        """Connect to service

        Returns:
            True if the connection was established"""
        pass

    @abc.abstractmethod
    def disconnect(self):
        """Disconnect"""
        pass

    @abc.abstractmethod
    def get_recent_emails(
        self,
        count: int = 20,
        only_unseen: bool = True,
    ) -> List[EmailMessage]:
        """Get recent emails

        Args:
            count: Number of emails to fetch
            only_unseen: Fetch only unread emails

        Returns:
            list of emails"""
        pass

    @abc.abstractmethod
    def test_connection(self) -> bool:
        """Test if the connection is working

        Returns:
            True if the connection is working"""
        pass

    def record_success(self):
        """Record a successful operation"""
        self._health.record_success()
        self._last_error = None
        logger.debug(f"[{self.account.email}] {self.provider_type.value} operation succeeded")

    def record_failure(self, error: str):
        """Record a provider failure"""
        self._health.record_failure(error)
        self._last_error = error

        # Check if it should be disabled
        if self._health.should_disable(self.config.health_failure_threshold):
            self._health.disable(self.config.health_disable_duration)
            logger.warning(
                f"[{self.account.email}] {self.provider_type.value} disabled"
                f"{self.config.health_disable_duration} seconds, reason: {error}"
            )
        else:
            logger.warning(
                f"[{self.account.email}] {self.provider_type.value} operation failed"
                f"({self._health.failure_count}/{self.config.health_failure_threshold}): {error}"
            )

    def check_health(self) -> bool:
        """Check health status

        Returns:
            True if healthy and available"""
        # Check if disabled
        if self._health.is_disabled():
            logger.debug(
                f"[{self.account.email}] {self.provider_type.value} is disabled,"
                f"Resumes at {self._health.disabled_until}"
            )
            return False

        return self._health.status in (ProviderStatus.HEALTHY, ProviderStatus.DEGRADED)

    def __enter__(self):
        """Enter the context manager and connect."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and disconnect."""
        self.disconnect()
        return False

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"{self.__class__.__name__}({self.account.email})"

    def __repr__(self) -> str:
        return self.__str__()
