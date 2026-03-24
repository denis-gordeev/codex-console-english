"""Legacy IMAP provider
Using outlook.office365.com server and login.live.com Token endpoint"""

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


logger = logging.getLogger(__name__)


class IMAPOldProvider(OutlookProvider):
    """Legacy IMAP provider
    Use outlook.office365.com:993 and login.live.com Token endpoints"""

    # IMAP server configuration
    IMAP_HOST = "outlook.office365.com"
    IMAP_PORT = 993

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.IMAP_OLD

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

    def connect(self) -> bool:
        """Connect to IMAP server

        Returns:
            Is the connection successful?"""
        if self._connected and self._conn:
            # Check existing connections
            try:
                self._conn.noop()
                return True
            except Exception:
                self.disconnect()

        try:
            logger.debug(f"[{self.account.email}] Connecting to IMAP ({self.IMAP_HOST})...")

            # Create connection
            self._conn = imaplib.IMAP4_SSL(
                self.IMAP_HOST,
                self.IMAP_PORT,
                timeout=self.config.timeout,
            )

            # Try XOAUTH2 authentication
            if self.account.has_oauth():
                if self._authenticate_xoauth2():
                    self._connected = True
                    self.record_success()
                    logger.info(f"[{self.account.email}] IMAP connection successful (XOAUTH2)")
                    return True
                else:
                    logger.warning(f"[{self.account.email}] XOAUTH2 authentication failed, try password authentication")

            # Password authentication
            if self.account.password:
                self._conn.login(self.account.email, self.account.password)
                self._connected = True
                self.record_success()
                logger.info(f"[{self.account.email}] IMAP connection successful (password authentication)")
                return True

            raise ValueError("No authentication method available")

        except Exception as e:
            self.disconnect()
            self.record_failure(str(e))
            logger.error(f"[{self.account.email}] IMAP connection failed: {e}")
            return False

    def _authenticate_xoauth2(self) -> bool:
        """Use XOAUTH2 authentication

        Returns:
            Whether the authentication is successful"""
        if not self._token_manager:
            self._token_manager = TokenManager(
                self.account,
                ProviderType.IMAP_OLD,
                self.config.proxy_url,
                self.config.timeout,
            )

        # Get Access Token
        token = self._token_manager.get_access_token()
        if not token:
            return False

        try:
            # Building the XOAUTH2 authentication string
            auth_string = f"user={self.account.email}\x01auth=Bearer {token}\x01\x01"
            self._conn.authenticate("XOAUTH2", lambda _: auth_string.encode("utf-8"))
            return True
        except Exception as e:
            logger.debug(f"[{self.account.email}] XOAUTH2 authentication exception: {e}")
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
            count: Get the quantity
            only_unseen: whether to only get unread

        Returns:
            mailing list"""
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
            recent_ids = ids[-count:][::-1]  # Reverse order, newest first

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
        """Get and parse a single email

        Args:
            msg_id: Email ID

        Returns:
            EmailMessage object, returns None on failure"""
        status, data = self._conn.fetch(msg_id, "(RFC822)")
        if status != "OK" or not data or not data[0]:
            return None

        # Get original email content
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
        """Parse the original email

        Args:
            raw: raw email data

        Returns:
            EmailMessage object"""
        # Remove BOM
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]

        msg = email.message_from_bytes(raw)

        # Parse email headers
        subject = IMAPOldProvider._decode_header(msg.get("Subject", ""))
        sender = IMAPOldProvider._decode_header(msg.get("From", ""))
        to = IMAPOldProvider._decode_header(msg.get("To", ""))
        delivered_to = IMAPOldProvider._decode_header(msg.get("Delivered-To", ""))
        x_original_to = IMAPOldProvider._decode_header(msg.get("X-Original-To", ""))
        date_str = IMAPOldProvider._decode_header(msg.get("Date", ""))

        # Extract text
        body = IMAPOldProvider._extract_body(msg)

        # parse date
        received_timestamp = 0
        received_at = None
        try:
            if date_str:
                received_at = parsedate_to_datetime(date_str)
                received_timestamp = int(received_at.timestamp())
        except Exception:
            pass

        # Build a recipient list
        recipients = [r for r in [to, delivered_to, x_original_to] if r]

        return EmailMessage(
            id=msg.get("Message-ID", ""),
            subject=subject,
            sender=sender,
            recipients=recipients,
            body=body,
            received_at=received_at,
            received_timestamp=received_timestamp,
            is_read=False,  # Searching for unread emails
            raw_data=raw[:500] if len(raw) > 500 else raw,
        )

    @staticmethod
    def _decode_header(header: str) -> str:
        """Decode email headers"""
        if not header:
            return ""

        parts = []
        for chunk, encoding in decode_header(header):
            if isinstance(chunk, bytes):
                try:
                    decoded = chunk.decode(encoding or "utf-8", errors="replace")
                    parts.append(decoded)
                except Exception:
                    parts.append(chunk.decode("utf-8", errors="replace"))
            else:
                parts.append(str(chunk))

        return "".join(parts).strip()

    @staticmethod
    def _extract_body(msg) -> str:
        """Extract email body"""
        import html as html_module
        import re

        texts = []
        parts = msg.walk() if msg.is_multipart() else [msg]

        for part in parts:
            content_type = part.get_content_type()
            if content_type not in ("text/plain", "text/html"):
                continue

            payload = part.get_payload(decode=True)
            if not payload:
                continue

            charset = part.get_content_charset() or "utf-8"
            try:
                text = payload.decode(charset, errors="replace")
            except LookupError:
                text = payload.decode("utf-8", errors="replace")

            # If it's HTML, remove tags
            if "<html" in text.lower():
                text = re.sub(r"<[^>]+>", " ", text)

            texts.append(text)

        # Merge and clean text
        combined = " ".join(texts)
        combined = html_module.unescape(combined)
        combined = re.sub(r"\s+", " ", combined).strip()

        return combined

    def test_connection(self) -> bool:
        """Test IMAP connection

        Returns:
            Is the connection normal?"""
        try:
            with self:
                self._conn.select("INBOX", readonly=True)
                self._conn.search(None, "ALL")
            return True
        except Exception as e:
            logger.warning(f"[{self.account.email}] IMAP connection test failed: {e}")
            return False
