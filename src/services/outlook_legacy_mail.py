"""
Outlook mailbox service implementation
Supports IMAP protocol, XOAUTH2 and password authentication
"""

import imaplib
import email
import re
import time
import threading
import json
import urllib.parse
import urllib.request
import base64
import hashlib
import secrets
import logging
from typing import Optional, Dict, Any, List
from email.header import decode_header
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError

from .base import BaseEmailService, EmailServiceError, EmailServiceType
from ..config.constants import (
    OTP_CODE_PATTERN,
    OTP_CODE_SIMPLE_PATTERN,
    OTP_CODE_SEMANTIC_PATTERN,
    OPENAI_EMAIL_SENDERS,
    OPENAI_VERIFICATION_KEYWORDS,
)
from ..config.settings import get_settings


def get_email_code_settings() -> dict:
    """
    Get verification code and wait for configuration

    Returns:
        dict: Dictionary containing timeout and poll_interval
    """
    settings = get_settings()
    return {
        "timeout": settings.email_code_timeout,
        "poll_interval": settings.email_code_poll_interval,
    }


logger = logging.getLogger(__name__)


class OutlookAccount:
    """Outlook account information"""

    def __init__(
        self,
        email: str,
        password: str,
        client_id: str = "",
        refresh_token: str = ""
    ):
        self.email = email
        self.password = password
        self.client_id = client_id
        self.refresh_token = refresh_token

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "OutlookAccount":
        """Create account from configuration"""
        return cls(
            email=config.get("email", ""),
            password=config.get("password", ""),
            client_id=config.get("client_id", ""),
            refresh_token=config.get("refresh_token", "")
        )

    def has_oauth(self) -> bool:
        """Does OAuth2 support"""
        return bool(self.client_id and self.refresh_token)

    def validate(self) -> bool:
        """Verify whether the account information is valid"""
        return bool(self.email and self.password) or self.has_oauth()


class OutlookIMAPClient:
    """
    Outlook IMAP client
    Supports XOAUTH2 and password authentication
    """

    #Microsoft OAuth2 Token cache
    _token_cache: Dict[str, tuple] = {}
    _cache_lock = threading.Lock()

    def __init__(
        self,
        account: OutlookAccount,
        host: str = "outlook.office365.com",
        port: int = 993,
        timeout: int = 20
    ):
        self.account = account
        self.host = host
        self.port = port
        self.timeout = timeout
        self._conn: Optional[imaplib.IMAP4_SSL] = None

    @staticmethod
    def refresh_ms_token(account: OutlookAccount, timeout: int = 15) -> str:
        """Refresh Microsoft access token"""
        if not account.client_id or not account.refresh_token:
            raise RuntimeError("Missing client_id or refresh_token")

        key = account.email.lower()
        with OutlookIMAPClient._cache_lock:
            cached = OutlookIMAPClient._token_cache.get(key)
            if cached and time.time() < cached[1]:
                return cached[0]

        body = urllib.parse.urlencode({
            "client_id": account.client_id,
            "refresh_token": account.refresh_token,
            "grant_type": "refresh_token",
            "redirect_uri": "https://login.live.com/oauth20_desktop.srf",
        }).encode()

        req = urllib.request.Request(
            "https://login.live.com/oauth20_token.srf",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
        except HTTPError as e:
            raise RuntimeError(f"MS OAuth refresh failed: {e.code}") from e

        token = data.get("access_token")
        if not token:
            raise RuntimeError("MS OAuth response no access_token")

        ttl = int(data.get("expires_in", 3600))
        with OutlookIMAPClient._cache_lock:
            OutlookIMAPClient._token_cache[key] = (token, time.time() + ttl - 120)

        return token

    @staticmethod
    def _build_xoauth2(email_addr: str, token: str) -> bytes:
        """Build XOAUTH2 authentication string"""
        return f"user={email_addr}\x01auth=Bearer {token}\x01\x01".encode()

    def connect(self):
        """Connect to IMAP server"""
        self._conn = imaplib.IMAP4_SSL(self.host, self.port, timeout=self.timeout)

        # Prioritize using XOAUTH2 authentication
        if self.account.has_oauth():
            try:
                token = self.refresh_ms_token(self.account)
                self._conn.authenticate(
                    "XOAUTH2",
                    lambda _: self._build_xoauth2(self.account.email, token)
                )
                logger.debug(f"Use XOAUTH2 authentication connection: {self.account.email}")
                return
            except Exception as e:
                logger.warning(f"XOAUTH2 authentication failed, fallback password authentication: {e}")

        # Fall back to password authentication
        self._conn.login(self.account.email, self.account.password)
        logger.debug(f"Use password authentication to connect: {self.account.email}")

    def _ensure_connection(self):
        """Make sure the connection is valid"""
        if self._conn:
            try:
                self._conn.noop()
                return
            except Exception:
                self.close()

        self.connect()

    def get_recent_emails(
        self,
        count: int = 20,
        only_unseen: bool = True,
        timeout: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get recent emails

        Args:
            count: the number of emails obtained
            only_unseen: whether to get only unread emails
            timeout: timeout time

        Returns:
            mailing list
        """
        self._ensure_connection()

        flag = "UNSEEN" if only_unseen else "ALL"
        self._conn.select("INBOX", readonly=True)

        _, data = self._conn.search(None, flag)
        if not data or not data[0]:
            return []

        # Get the latest email
        ids = data[0].split()[-count:]
        result = []

        for mid in reversed(ids):
            try:
                _, payload = self._conn.fetch(mid, "(RFC822)")
                if not payload:
                    continue

                raw = b""
                for part in payload:
                    if isinstance(part, tuple) and len(part) > 1:
                        raw = part[1]
                        break

                if raw:
                    result.append(self._parse_email(raw))
            except Exception as e:
                logger.warning(f"Failed to parse email (ID: {mid}): {e}")

        return result

    @staticmethod
    def _parse_email(raw: bytes) -> Dict[str, Any]:
        """Parse the email content"""
        # Remove possible BOM
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]

        msg = email.message_from_bytes(raw)

        # Parse email headers
        subject = OutlookIMAPClient._decode_header(msg.get("Subject", ""))
        sender = OutlookIMAPClient._decode_header(msg.get("From", ""))
        date_str = OutlookIMAPClient._decode_header(msg.get("Date", ""))
        to = OutlookIMAPClient._decode_header(msg.get("To", ""))
        delivered_to = OutlookIMAPClient._decode_header(msg.get("Delivered-To", ""))
        x_original_to = OutlookIMAPClient._decode_header(msg.get("X-Original-To", ""))

        # Extract email body
        body = OutlookIMAPClient._extract_body(msg)

        # Parse date
        date_timestamp = 0
        try:
            if date_str:
                dt = parsedate_to_datetime(date_str)
                date_timestamp = int(dt.timestamp())
        except Exception:
            pass

        return {
            "subject": subject,
            "from": sender,
            "date": date_str,
            "date_timestamp": date_timestamp,
            "to": to,
            "delivered_to": delivered_to,
            "x_original_to": x_original_to,
            "body": body,
            "raw": raw.hex()[:100] # Store a partial hash of the original data for debugging
        }

    @staticmethod
    def _decode_header(header: str) -> str:
        """Decoding email headers"""
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
                parts.append(chunk)

        return "".join(parts).strip()

    @staticmethod
    def _extract_body(msg) -> str:
        """Extract email text"""
        import html as html_module

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

    def close(self):
        """Close connection"""
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

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class OutlookService(BaseEmailService):
    """
    Outlook mailbox service
    Supports polling and verification code acquisition for multiple Outlook accounts
    """

    def __init__(self, config: Dict[str, Any] = None, name: str = None):
        """
        Initialize the Outlook service

        Args:
            config: configuration dictionary, supports the following keys:
                - accounts: Outlook account list, each account contains:
                  - email: email address
                  - password: password
                  - client_id: OAuth2 client_id (optional)
                  - refresh_token: OAuth2 refresh_token (optional)
                - imap_host: IMAP server (default: outlook.office365.com)
                - imap_port: IMAP port (default: 993)
                - timeout: timeout (default: 30)
                - max_retries: Maximum number of retries (default: 3)
            name: service name
        """
        super().__init__(EmailServiceType.OUTLOOK, name)

        #Default configuration
        default_config = {
            "accounts": [],
            "imap_host": "outlook.office365.com",
            "imap_port": 993,
            "timeout": 30,
            "max_retries": 3,
            "proxy_url": None,
        }

        self.config = {**default_config, **(config or {})}

        # Parse account
        self.accounts: List[OutlookAccount] = []
        self._current_account_index = 0
        self._account_locks: Dict[str, threading.Lock] = {}

        # Supports two configuration formats:
        # 1. Single account format: {"email": "xxx", "password": "xxx"}
        # 2. Multiple account format: {"accounts": [{"email": "xxx", "password": "xxx"}]}
        if "email" in self.config and "password" in self.config:
            # Single account format
            account = OutlookAccount.from_config(self.config)
            if account.validate():
                self.accounts.append(account)
                self._account_locks[account.email] = threading.Lock()
            else:
                logger.warning(f"Invalid Outlook account configuration: {self.config}")
        else:
            #Multiple account format
            for account_config in self.config.get("accounts", []):
                account = OutlookAccount.from_config(account_config)
                if account.validate():
                    self.accounts.append(account)
                    self._account_locks[account.email] = threading.Lock()
                else:
                    logger.warning(f"Invalid Outlook account configuration: {account_config}")

        if not self.accounts:
            logger.warning("No valid Outlook account configured")

        # IMAP connection limit (prevent current limiting)
        self._imap_semaphore = threading.Semaphore(5)

        # Verification code deduplication mechanism: email -> set of used codes
        self._used_codes: Dict[str, set] = {}

    def create_email(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Select an available Outlook account

        Args:
            config: Configuration parameters (currently not used)

        Returns:
            Dictionary containing email information:
            - email: email address
            - service_id: account email (same as email)
            - account: account information
        """
        if not self.accounts:
            self.update_status(False, EmailServiceError("No Outlook account available"))
            raise EmailServiceError("No Outlook account available")

        # Poll to select account
        with threading.Lock():
            account = self.accounts[self._current_account_index]
            self._current_account_index = (self._current_account_index + 1) % len(self.accounts)

        email_info = {
            "email": account.email,
            "service_id": account.email, # For Outlook, service_id is the email address
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
        pattern: str = OTP_CODE_PATTERN,
        otp_sent_at: Optional[float] = None,
    ) -> Optional[str]:
        """
        Get verification code from Outlook mailbox

        Args:
            email: email address
            email_id: Not used (for Outlook, email is the ID)
            timeout: timeout time (seconds), the configuration value is used by default
            pattern: verification code regular expression
            otp_sent_at: OTP sending timestamp, used to filter old emails

        Returns:
            Verification code string, returns None if timeout or not found
        """
        # Find the corresponding account
        account = None
        for acc in self.accounts:
            if acc.email.lower() == email.lower():
                account = acc
                break

        if not account:
            self.update_status(False, EmailServiceError(f"The account corresponding to the email address was not found: {email}"))
            return None

        # Get the verification code from the database and wait for configuration
        code_settings = get_email_code_settings()
        actual_timeout = timeout or code_settings["timeout"]
        poll_interval = code_settings["poll_interval"]

        logger.info(f"[{email}] starts to obtain the verification code, timeout {actual_timeout}s, OTP sending time: {otp_sent_at}")

        # Initialize verification code deduplication collection
        if email not in self._used_codes:
            self._used_codes[email] = set()
        used_codes = self._used_codes[email]

        # Calculate minimum timestamp (allow 60 seconds clock offset)
        min_timestamp = (otp_sent_at - 60) if otp_sent_at else 0

        start_time = time.time()
        poll_count = 0

        while time.time() - start_time < actual_timeout:
            poll_count += 1
            loop_start = time.time()

            # Progressive email checking: only check unread messages for the first 3 times, then check all
            only_unseen = poll_count <= 3

            try:
                connect_start = time.time()
                with self._imap_semaphore:
                    with OutlookIMAPClient(
                        account,
                        host=self.config["imap_host"],
                        port=self.config["imap_port"],
                        timeout=10
                    ) as client:
                        connect_elapsed = time.time() - connect_start
                        logger.debug(f"[{email}] IMAP connection took {connect_elapsed:.2f}s")

                        # Search mail
                        search_start = time.time()
                        emails = client.get_recent_emails(count=15, only_unseen=only_unseen)
                        search_elapsed = time.time() - search_start
                        logger.debug(f"[{email}] searched {len(emails)} emails (unread={only_unseen}), which took {search_elapsed:.2f}s")

                        for mail in emails:
                            # Timestamp filtering
                            mail_ts = mail.get("date_timestamp", 0)
                            if min_timestamp > 0 and mail_ts > 0 and mail_ts < min_timestamp:
                                logger.debug(f"[{email}] Skip old emails: {mail.get('subject', '')[:50]}")
                                continue

                            # Check if it is an OpenAI verification email
                            if not self._is_openai_verification_mail(mail, email):
                                continue

                            # Extract verification code
                            code = self._extract_code_from_mail(mail, pattern)
                            if code:
                                # Deduplication check
                                if code in used_codes:
                                    logger.debug(f"[{email}] Skip the used verification code: {code}")
                                    continue

                                used_codes.add(code)
                                elapsed = int(time.time() - start_time)
                                logger.info(f"[{email}] found verification code: {code}, total time spent {elapsed}s, polling {poll_count} times")
                                self.update_status(True)
                                return code

            except Exception as e:
                loop_elapsed = time.time() - loop_start
                logger.warning(f"[{email}] check error: {e}, loop takes {loop_elapsed:.2f}s")

            # Wait for next polling
            time.sleep(poll_interval)

        elapsed = int(time.time() - start_time)
        logger.warning(f"[{email}] verification code timeout ({actual_timeout}s), total polling {poll_count} times")
        return None

    def list_emails(self, **kwargs) -> List[Dict[str, Any]]:
        """
        List all available Outlook accounts

        Returns:
            Account list
        """
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
        """
        Delete a mailbox (for Outlook, deleting an account is not supported)

        Args:
            email_id: email address

        Returns:
            False (Outlook does not support deleting accounts)
        """
        logger.warning(f"Outlook service does not support deletion of account: {email_id}")
        return False

    def check_health(self) -> bool:
        """Check whether the Outlook service is available"""
        if not self.accounts:
            self.update_status(False, EmailServiceError("No account configured"))
            return False

        # Test the connection of the first account
        test_account = self.accounts[0]
        try:
            with self._imap_semaphore:
                with OutlookIMAPClient(
                    test_account,
                    host=self.config["imap_host"],
                    port=self.config["imap_port"],
                    timeout=10
                ) as client:
                    # Try listing mailboxes (quick test)
                    client._conn.select("INBOX", readonly=True)
                    self.update_status(True)
                    return True
        except Exception as e:
            logger.warning(f"Outlook health check failed ({test_account.email}): {e}")
            self.update_status(False, e)
            return False

    def _is_oai_mail(self, mail: Dict[str, Any]) -> bool:
        """Determine whether it is an OpenAI related email (old method, retained for compatibility)"""
        combined = f"{mail.get('from', '')} {mail.get('subject', '')} {mail.get('body', '')}".lower()
        keywords = ["openai", "chatgpt", "verification", "verification code", "code"]
        return any(keyword in combined for keyword in keywords)

    def _is_openai_verification_mail(
        self,
        mail: Dict[str, Any],
        target_email: str = None
    ) -> bool:
        """
        Strictly judge whether it is an OpenAI verification email

        Args:
            mail: mail information dictionary
            target_email: target email address (used to verify recipients)

        Returns:
            Whether to verify email for OpenAI
        """
        sender = mail.get("from", "").lower()

        # 1. The sender must be OpenAI
        valid_senders = OPENAI_EMAIL_SENDERS
        if not any(s in sender for s in valid_senders):
            logger.debug(f"The email sender is not OpenAI: {sender}")
            return False

        # 2. The subject or text contains verification keywords
        subject = mail.get("subject", "").lower()
        body = mail.get("body", "").lower()
        verification_keywords = OPENAI_VERIFICATION_KEYWORDS
        combined = f"{subject} {body}"
        if not any(kw in combined for kw in verification_keywords):
            logger.debug(f"The email does not contain the verification keyword: {subject[:50]}")
            return False

        # 3. Verify recipient (optional)
        if target_email:
            recipients = f"{mail.get('to', '')} {mail.get('delivered_to', '')} {mail.get('x_original_to', '')}".lower()
            if target_email.lower() not in recipients:
                logger.debug(f"Mail recipient does not match: {recipients[:50]}")
                return False

        logger.debug(f"Identified as OpenAI verification email: {subject[:50]}")
        return True

    def _extract_code_from_mail(
        self,
        mail: Dict[str, Any],
        fallback_pattern: str = OTP_CODE_PATTERN
    ) -> Optional[str]:
        """
        Extract verification code from email

        Priority:
        1. Extract from topic (6 digits)
        2. Use semantic regular extraction from the text (such as "code is 123456")
        3. Guarantee: any 6-digit number

        Args:
            mail: mail information dictionary
            fallback_pattern: back-up regular expression

        Returns:
            Verification code string, returns None if not found
        """
        #Compile regular
        re_simple = re.compile(OTP_CODE_SIMPLE_PATTERN)
        re_semantic = re.compile(OTP_CODE_SEMANTIC_PATTERN, re.IGNORECASE)

        # 1. Topic priority
        subject = mail.get("subject", "")
        match = re_simple.search(subject)
        if match:
            code = match.group(1)
            logger.debug(f"Extract verification code from topic: {code}")
            return code

        # 2. Text semantic matching
        body = mail.get("body", "")
        match = re_semantic.search(body)
        if match:
            code = match.group(1)
            logger.debug(f"Extract verification code from text semantics: {code}")
            return code

        # 3. Guarantee: any 6-digit number
        match = re_simple.search(body)
        if match:
            code = match.group(1)
            logger.debug(f"Extract the verification code from the bottom of the text: {code}")
            return code

        return None

    def get_account_stats(self) -> Dict[str, Any]:
        """Get account statistics"""
        total = len(self.accounts)
        oauth_count = sum(1 for acc in self.accounts if acc.has_oauth())

        return {
            "total_accounts": total,
            "oauth_accounts": oauth_count,
            "password_accounts": total - oauth_count,
            "accounts": [
                {
                    "email": acc.email,
                    "has_oauth": acc.has_oauth()
                }
                for acc in self.accounts
            ]
        }

    def add_account(self, account_config: Dict[str, Any]) -> bool:
        """Add new Outlook account"""
        try:
            account = OutlookAccount.from_config(account_config)
            if not account.validate():
                return False

            self.accounts.append(account)
            self._account_locks[account.email] = threading.Lock()
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
                self._account_locks.pop(email, None)
                logger.info(f"Remove Outlook account: {email}")
                return True
        return False