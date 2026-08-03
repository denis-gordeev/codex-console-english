"""New IMAP provider
Using the outlook.live.com server and the login.microsoftonline.com/consumers Token endpoint"""

import email
import imaplib
import logging
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import List, Optional

from ..base import ProviderType, EmailMessage
from ..account import OutlookAccount
from ..token_manager import TokenManager
from .base import OutlookProvider, ProviderConfig
from .imap_old import IMAPOldProvider


logger = logging.getLogger(__name__)


class IMAPNewProvider(OutlookProvider):
    """New IMAP provider
    Use outlook.live.com:993 and login.microsoftonline.com/consumers Token endpoints
    Requires IMAP.AccessAsUser.All scope"""

    # IMAP server settings
    IMAP_HOST = "outlook.live.com"
    IMAP_PORT = 993

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.IMAP_NEW

    def __init__(
        self,
        account: OutlookAccount,
        config: Optional[ProviderConfig] = None,
    ):
        super().__init__(account, config)

        # IMAP connection
        self._conn: Optional[imaplib.IMAP4_SSL] = None

        # Token Manager
        self._token_manager: Optional[TokenManager] = None

        # Note: New versions of IMAP must use OAuth2
        if not account.has_oauth():
            logger.warning(
                f"[{self.account.email}] New IMAP provider requires OAuth2 credentials"
                f"(client_id + refresh_token)"
            )

    def connect(self) -> bool:
        """Connect to IMAP server

        Returns:
            True if the connection succeeds"""
        if self._connected and self._conn:
            try:
                self._conn.noop()
                return True
            except Exception:
                self.disconnect()

        # New IMAP requires OAuth2; without OAuth, the provider is skipped without recording a health failure.
        if not self.account.has_oauth():
            logger.debug(f"[{self.account.email}] Skipping IMAP_NEW (no OAuth)")
            return False

        try:
            logger.debug(f"[{self.account.email}] Connecting to IMAP ({self.IMAP_HOST})...")

            # Create connection
            self._conn = imaplib.IMAP4_SSL(
                self.IMAP_HOST,
                self.IMAP_PORT,
                timeout=self.config.timeout,
            )

            # XOAUTH2 certification
            if self._authenticate_xoauth2():
                self._connected = True
                self.record_success()
                logger.info(f"[{self.account.email}] New IMAP connected (XOAUTH2)")
                return True

            return False

        except Exception as e:
            self.disconnect()
            self.record_failure(str(e))
            logger.error(f"[{self.account.email}] New IMAP connection failed: {e}")
            return False

    def _authenticate_xoauth2(self) -> bool:
        """Authenticate with XOAUTH2

        Returns:
            True if authentication succeeds"""
        if not self._token_manager:
            self._token_manager = TokenManager(
                self.account,
                ProviderType.IMAP_NEW,
                self.config.proxy_url,
                self.config.timeout,
            )

        # Get Access Token
        token = self._token_manager.get_access_token()
        if not token:
            logger.error(f"[{self.account.email}] Failed to get IMAP Token")
            return False

        try:
            # Build the XOAUTH2 auth string
            auth_string = f"user={self.account.email}\x01auth=Bearer {token}\x01\x01"
            self._conn.authenticate("XOAUTH2", lambda _: auth_string.encode("utf-8"))
            return True
        except Exception as e:
            logger.error(f"[{self.account.email}] XOAUTH2 authentication error: {e}")
            # Clear cached tokens
            self._token_manager.clear_cache()
            return False

    def disconnect(self):
        """Disconnect IMAP"""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None

        self._connected = False

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
        if not self._connected:
            if not self.connect():
                return []

        try:
            # Select inbox
            self._conn.select("INBOX", readonly=True)

            # Search mail
            flag = "UNSEEN" if only_unseen else "ALL"
            status, data = self._conn.search(None, flag)

            if status != "OK" or not data or not data[0]:
                return []

            # Get latest email id
            ids = data[0].split()
            recent_ids = ids[-count:][::-1]

            emails = []
            for msg_id in recent_ids:
                try:
                    email_msg = self._fetch_email(msg_id)
                    if email_msg:
                        emails.append(email_msg)
                except Exception as e:
                    logger.warning(f"[{self.account.email}] Failed to parse email (ID: {msg_id}): {e}")

            return emails

        except Exception as e:
            self.record_failure(str(e))
            logger.error(f"[{self.account.email}] Failed to get email: {e}")
            return []

    def _fetch_email(self, msg_id: bytes) -> Optional[EmailMessage]:
        """Get and parse a single email"""
        status, data = self._conn.fetch(msg_id, "(RFC822)")
        if status != "OK" or not data or not data[0]:
            return None

        raw = b""
        for part in data:
            if isinstance(part, tuple) and len(part) > 1:
                raw = part[1]
                break

        if not raw:
            return None

        return self._parse_email(raw)

    @staticmethod
    def _parse_email(raw: bytes) -> EmailMessage:
        """Parse raw email"""
        # Reuse the legacy provider's email parsing
        return IMAPOldProvider._parse_email(raw)

    def test_connection(self) -> bool:
        """Test IMAP connection"""
        try:
            with self:
                self._conn.select("INBOX", readonly=True)
                self._conn.search(None, "ALL")
            return True
        except Exception as e:
            logger.warning(f"[{self.account.email}] New IMAP connection test failed: {e}")
            return False
