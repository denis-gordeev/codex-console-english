"""
Outlook email service main class
Support multiple IMAP/API connection methods, automatic failover
"""

import logging
import threading
import time
from typing import Optional, Dict, Any, List

from ..base import BaseEmailService, EmailServiceError, EmailServiceStatus, EmailServiceType
from ...config.constants import EmailServiceType as ServiceType
from ...config.settings import get_settings
from .account import OutlookAccount
from .base import ProviderType, EmailMessage
from .email_parser import EmailParser, get_email_parser
from .health_checker import HealthChecker, FailoverManager
from .providers.base import OutlookProvider, ProviderConfig
from .providers.imap_old import IMAPOldProvider
from .providers.imap_new import IMAPNewProvider
from .providers.graph_api import GraphAPIProvider


logger = logging.getLogger(__name__)


# Default provider priority
# IMAP_OLD is the most compatible (only login.live.com token is required), IMAP_NEW is second, and Graph API is last
# Reason: Some client_ids do not have Graph API permissions, but have IMAP permissions
DEFAULT_PROVIDER_PRIORITY = [
    ProviderType.IMAP_OLD,
    ProviderType.IMAP_NEW,
    ProviderType.GRAPH_API,
]


def get_email_code_settings() -> dict:
    """Get OTP polling settings (timeout and interval)"""
    settings = get_settings()
    return {
        "timeout": settings.email_code_timeout,
        "poll_interval": settings.email_code_poll_interval,
    }


class OutlookService(BaseEmailService):
    """
    Outlook email service
    Support multiple IMAP/API connection methods, automatic failover
    """

    def __init__(self, config: Dict[str, Any] = None, name: str = None):
        """
        Initialize the Outlook service

        Args:
            config: settings dict with the following keys:
                - accounts: Outlook account list
                - provider_priority: provider priority list
                - health_failure_threshold: Consecutive failure threshold
                - health_disable_duration: How long to disable the provider (seconds)
                - timeout: request timeout
                - proxy_url: proxy URL
            name: service name
        """
        super().__init__(ServiceType.OUTLOOK, name)

        # Default settings
        default_config = {
            "accounts": [],
            "provider_priority": [p.value for p in DEFAULT_PROVIDER_PRIORITY],
            "health_failure_threshold": 5,
            "health_disable_duration": 60,
            "timeout": 30,
            "proxy_url": None,
        }

        self.config = {**default_config, **(config or {})}

        # Parse provider priority
        self.provider_priority = [
            ProviderType(p) for p in self.config.get("provider_priority", [])
        ]
        if not self.provider_priority:
            self.provider_priority = DEFAULT_PROVIDER_PRIORITY

        # Provider settings
        self.provider_config = ProviderConfig(
            timeout=self.config.get("timeout", 30),
            proxy_url=self.config.get("proxy_url"),
            health_failure_threshold=self.config.get("health_failure_threshold", 3),
            health_disable_duration=self.config.get("health_disable_duration", 300),
        )

        # Use the default client_id (for accounts without client_id)
        try:
            _default_client_id = get_settings().outlook_default_client_id
        except Exception:
            _default_client_id = "24d9a0ed-8787-4584-883c-2fd79308940a"

        # Parse account
        self.accounts: List[OutlookAccount] = []
        self._current_account_index = 0
        self._account_lock = threading.Lock()

        # Support two settings formats
        if "email" in self.config and "password" in self.config:
            account = OutlookAccount.from_config(self.config)
            if not account.client_id and _default_client_id:
                account.client_id = _default_client_id
            if account.validate():
                self.accounts.append(account)
        else:
            for account_config in self.config.get("accounts", []):
                account = OutlookAccount.from_config(account_config)
                if not account.client_id and _default_client_id:
                    account.client_id = _default_client_id
                if account.validate():
                    self.accounts.append(account)

        if not self.accounts:
            logger.warning("No valid Outlook account configured")

        # Health Checker and Failover Manager
        self.health_checker = HealthChecker(
            failure_threshold=self.provider_config.health_failure_threshold,
            disable_duration=self.provider_config.health_disable_duration,
        )
        self.failover_manager = FailoverManager(
            health_checker=self.health_checker,
            priority_order=self.provider_priority,
        )

        # Email parser
        self.email_parser = get_email_parser()

        # Provider instance cache: (email, provider_type) -> OutlookProvider
        self._providers: Dict[tuple, OutlookProvider] = {}
        self._provider_lock = threading.Lock()

        # IMAP connection limit (prevent rate limiting)
        self._imap_semaphore = threading.Semaphore(5)

        # OTP dedup tracking
        self._used_codes: Dict[str, set] = {}

    def _get_provider(
        self,
        account: OutlookAccount,
        provider_type: ProviderType,
    ) -> OutlookProvider:
        """
        Get or create a provider instance

        Args:
            account: Outlook account
            provider_type: provider type

        Returns:
            provider instance
        """
        cache_key = (account.email.lower(), provider_type)

        with self._provider_lock:
            if cache_key not in self._providers:
                provider = self._create_provider(account, provider_type)
                self._providers[cache_key] = provider

            return self._providers[cache_key]

    def _create_provider(
        self,
        account: OutlookAccount,
        provider_type: ProviderType,
    ) -> OutlookProvider:
        """
        Create provider instance

        Args:
            account: Outlook account
            provider_type: provider type

        Returns:
            provider instance
        """
        if provider_type == ProviderType.IMAP_OLD:
            return IMAPOldProvider(account, self.provider_config)
        elif provider_type == ProviderType.IMAP_NEW:
            return IMAPNewProvider(account, self.provider_config)
        elif provider_type == ProviderType.GRAPH_API:
            return GraphAPIProvider(account, self.provider_config)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    def _get_provider_priority_for_account(self, account: OutlookAccount) -> List[ProviderType]:
        """Return a prioritized list of suitable providers, depending on whether the account has OAuth"""
        if account.has_oauth():
            return self.provider_priority
        else:
            # No OAuth -- fall back to legacy IMAP (password authentication), skip providers that require OAuth
            return [ProviderType.IMAP_OLD]

    def _try_providers_for_emails(
        self,
        account: OutlookAccount,
        count: int = 20,
        only_unseen: bool = True,
    ) -> List[EmailMessage]:
        """
        Try multiple providers to get mail

        Args:
            account: Outlook account
            count: Number of emails to fetch
            only_unseen: Fetch only unread emails

        Returns:
            list of emails
        """
        errors = []

        # Select the appropriate provider priority based on account type
        priority = self._get_provider_priority_for_account(account)

        # Try each provider in order of priority
        for provider_type in priority:
            # Skip unavailable providers
            if not self.health_checker.is_available(provider_type):
                logger.debug(
                    f"[{account.email}] {provider_type.value} not available, skipping"
                )
                continue

            try:
                provider = self._get_provider(account, provider_type)

                with self._imap_semaphore:
                    with provider:
                        emails = provider.get_recent_emails(count, only_unseen)

                        if emails:
                            # Emails retrieved
                            self.health_checker.record_success(provider_type)
                            logger.debug(
                                f"[{account.email}] {provider_type.value} got {len(emails)} emails"
                            )
                            return emails

            except Exception as e:
                error_msg = str(e)
                errors.append(f"{provider_type.value}: {error_msg}")
                self.health_checker.record_failure(provider_type, error_msg)
                logger.warning(
                    f"[{account.email}] {provider_type.value} failed to get email: {e}"
                )

        logger.error(
            f"[{account.email}] All providers failed: {'; '.join(errors)}"
        )
        return []

    def create_email(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Select an available Outlook account

        Args:
            config: Settings options (unused)

        Returns:
            Dictionary containing email data
        """
        if not self.accounts:
            self.update_status(False, EmailServiceError("No Outlook account available"))
            raise EmailServiceError("No Outlook account available")

        # Poll to select account
        with self._account_lock:
            account = self.accounts[self._current_account_index]
            self._current_account_index = (self._current_account_index + 1) % len(self.accounts)

        email_info = {
            "email": account.email,
            "service_id": account.email,
            "account": {
                "email": account.email,
                "has_oauth": account.has_oauth()
            }
        }

        logger.info(f"Select Outlook account: {account.email}")
        self.update_status(True)
        return email_info

    def get_verification_code(
        self,
        email: str,
        email_id: str = None,
        timeout: int = None,
        pattern: str = None,
        otp_sent_at: Optional[float] = None,
    ) -> Optional[str]:
        """
        Get OTP from Outlook email

        Args:
            email: email address
            email_id: Not used
            timeout: timeout (seconds)
            pattern: OTP regex pattern (not used)
            otp_sent_at: OTP sent timestamp

        Returns:
            OTP string
        """
        # Find the matching account
        account = None
        for acc in self.accounts:
            if acc.email.lower() == email.lower():
                account = acc
                break

        if not account:
            self.update_status(False, EmailServiceError(f"No account found for email: {email}"))
            return None

        # Load OTP retrieval settings
        code_settings = get_email_code_settings()
        actual_timeout = timeout or code_settings["timeout"]
        poll_interval = code_settings["poll_interval"]

        logger.info(
            f"[{email}] fetching OTP, timeout {actual_timeout}s,"
            f"Provider priority: {[p.value for p in self.provider_priority]}"
        )

        # Initialize OTP dedup set
        if email not in self._used_codes:
            self._used_codes[email] = set()
        used_codes = self._used_codes[email]

        # Calculate minimum timestamp (allow 60 seconds of clock drift)
        min_timestamp = (otp_sent_at - 60) if otp_sent_at else 0

        start_time = time.time()
        poll_count = 0

        while time.time() - start_time < actual_timeout:
            poll_count += 1

            # Progressive email checking: only check unread items in the first 3 times
            only_unseen = poll_count <= 3

            try:
                # Try multiple providers to get mail
                emails = self._try_providers_for_emails(
                    account,
                    count=15,
                    only_unseen=only_unseen,
                )

                if emails:
                    logger.debug(
                        f"[{email}] fetched {len(emails)} emails in poll #{poll_count}"
                    )

                    # Find the OTP in the email
                    code = self.email_parser.find_verification_code_in_emails(
                        emails,
                        target_email=email,
                        min_timestamp=min_timestamp,
                        used_codes=used_codes,
                    )

                    if code:
                        used_codes.add(code)
                        elapsed = int(time.time() - start_time)
                        logger.info(
                            f"[{email}] found OTP: {code},"
                            f"elapsed {elapsed}s, after {poll_count} polls"
                        )
                        self.update_status(True)
                        return code

            except Exception as e:
                logger.warning(f"[{email}] check failed: {e}")

            # Wait before next poll
            time.sleep(poll_interval)

        elapsed = int(time.time() - start_time)
        logger.warning(f"[{email}] OTP timeout ({actual_timeout}s) after {poll_count} polls")
        return None

    def list_emails(self, **kwargs) -> List[Dict[str, Any]]:
        """List all available Outlook accounts"""
        return [
            {
                "email": account.email,
                "id": account.email,
                "has_oauth": account.has_oauth(),
                "type": "outlook"
            }
            for account in self.accounts
        ]

    def delete_email(self, email_id: str) -> bool:
        """Delete email address (Outlook does not support deleting accounts)"""
        logger.warning(f"Outlook service does not support account deletion: {email_id}")
        return False

    def check_health(self) -> bool:
        """Check if the Outlook service is available"""
        if not self.accounts:
            self.update_status(False, EmailServiceError("No account configured"))
            return False

        # Test the first account's connection
        test_account = self.accounts[0]

        # Try any provider connection
        for provider_type in self.provider_priority:
            try:
                provider = self._get_provider(test_account, provider_type)
                if provider.test_connection():
                    self.update_status(True)
                    return True
            except Exception as e:
                logger.warning(
                    f"Outlook health check failed ({test_account.email}, {provider_type.value}): {e}"
                )

        self.update_status(False, EmailServiceError("Health check failed"))
        return False

    def get_provider_status(self) -> Dict[str, Any]:
        """Get provider status"""
        return self.failover_manager.get_status()

    def get_account_stats(self) -> Dict[str, Any]:
        """Get account statistics"""
        total = len(self.accounts)
        oauth_count = sum(1 for acc in self.accounts if acc.has_oauth())

        return {
            "total_accounts": total,
            "oauth_accounts": oauth_count,
            "password_accounts": total - oauth_count,
            "accounts": [acc.to_dict() for acc in self.accounts],
            "provider_status": self.get_provider_status(),
        }

    def add_account(self, account_config: Dict[str, Any]) -> bool:
        """Add new Outlook account"""
        try:
            account = OutlookAccount.from_config(account_config)
            if not account.validate():
                return False

            self.accounts.append(account)
            logger.info(f"Add Outlook account: {account.email}")
            return True
        except Exception as e:
            logger.error(f"Failed to add Outlook account: {e}")
            return False

    def remove_account(self, email: str) -> bool:
        """Remove Outlook account"""
        for i, acc in enumerate(self.accounts):
            if acc.email.lower() == email.lower():
                self.accounts.pop(i)
                logger.info(f"Remove Outlook account: {email}")
                return True
        return False

    def reset_provider_health(self):
        """Reset all provider health statuses"""
        self.health_checker.reset_all()
        logger.info("All provider health statuses reset")

    def force_provider(self, provider_type: ProviderType):
        """Force the specified provider"""
        self.health_checker.force_enable(provider_type)
        # Disable other providers
        for pt in ProviderType:
            if pt != provider_type:
                self.health_checker.force_disable(pt, 60)
        logger.info(f"Provider force-set to: {provider_type.value}")
