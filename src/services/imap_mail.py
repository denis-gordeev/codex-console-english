"""
IMAP email service
Supports standard IMAP protocol email service providers such as Gmail / QQ / 163 / Yahoo / Outlook.
Only used to receive verification codes, forcing direct connection (imaplib does not support proxy).
"""

import imaplib
import email
import re
import time
import logging
from email.header import decode_header
from typing import Any, Dict, Optional

from .base import BaseEmailService, EmailServiceError
from ..config.constants import (
    EmailServiceType,
    OPENAI_EMAIL_SENDERS,
    OTP_CODE_SEMANTIC_PATTERN,
    OTP_CODE_PATTERN,
)

logger = logging.getLogger(__name__)


class ImapMailService(BaseEmailService):
    """Standard IMAP email service (only receives verification code, forced direct connection)"""

    def __init__(self, config: Dict[str, Any] = None, name: str = None):
        super().__init__(EmailServiceType.IMAP_MAIL, name)

        cfg = config or {}
        required_keys = ["host", "email", "password"]
        missing_keys = [k for k in required_keys if not cfg.get(k)]
        if missing_keys:
            raise ValueError(f"Missing required configuration: {missing_keys}")

        self.host: str = str(cfg["host"]).strip()
        self.port: int = int(cfg.get("port", 993))
        self.use_ssl: bool = bool(cfg.get("use_ssl", True))
        self.email_addr: str = str(cfg["email"]).strip()
        self.password: str = str(cfg["password"])
        self.timeout: int = int(cfg.get("timeout", 30))
        self.max_retries: int = int(cfg.get("max_retries", 3))

    def _connect(self) -> imaplib.IMAP4:
        """Establish IMAP connection and log in, return mail object"""
        if self.use_ssl:
            mail = imaplib.IMAP4_SSL(self.host, self.port)
        else:
            mail = imaplib.IMAP4(self.host, self.port)
            mail.starttls()
        mail.login(self.email_addr, self.password)
        return mail

    def _decode_str(self, value) -> str:
        """Decoding email header fields"""
        if value is None:
            return ""
        parts = decode_header(value)
        decoded = []
        for part, charset in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                decoded.append(str(part))
        return " ".join(decoded)

    def _get_text_body(self, msg) -> str:
        """Extract the plain text content of the email"""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    charset = part.get_content_charset() or "utf-8"
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode(charset, errors="replace")
        else:
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode(charset, errors="replace")
        return body

    def _is_openai_sender(self, from_addr: str) -> bool:
        """Determine whether the sender is OpenAI"""
        from_lower = from_addr.lower()
        for sender in OPENAI_EMAIL_SENDERS:
            if sender.startswith("@") or sender.startswith("."):
                if sender in from_lower:
                    return True
            else:
                if sender in from_lower:
                    return True
        return False

    def _extract_otp(self, text: str) -> Optional[str]:
        """Extract the 6-digit verification code from the text, giving priority to semantic matching and falling back to simple matching"""
        match = re.search(OTP_CODE_SEMANTIC_PATTERN, text, re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.search(OTP_CODE_PATTERN, text)
        if match:
            return match.group(1)
        return None

    def create_email(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """IMAP mode does not create a new mailbox and directly returns the fixed address in the configuration"""
        self.update_status(True)
        return {
            "email": self.email_addr,
            "service_id": self.email_addr,
            "id": self.email_addr,
        }

    def get_verification_code(
        self,
        email: str,
        email_id: str = None,
        timeout: int = 60,
        pattern: str = None,
        otp_sent_at: Optional[float] = None,
    ) -> Optional[str]:
        """Poll IMAP inbox for OpenAI verification code"""
        start_time = time.time()
        seen_ids: set = set()
        mail = None

        try:
            mail = self._connect()
            mail.select("INBOX")

            while time.time() - start_time < timeout:
                try:
                    # Search all unread emails
                    status, data = mail.search(None, "UNSEEN")
                    if status != "OK" or not data or not data[0]:
                        time.sleep(3)
                        continue

                    msg_ids = data[0].split()
                    for msg_id in reversed(msg_ids): # Newest first
                        id_str = msg_id.decode()
                        if id_str in seen_ids:
                            continue
                        seen_ids.add(id_str)

                        # Get mail
                        status, msg_data = mail.fetch(msg_id, "(RFC822)")
                        if status != "OK" or not msg_data:
                            continue

                        raw = msg_data[0][1]
                        msg = email.message_from_bytes(raw)

                        # Check sender
                        from_addr = self._decode_str(msg.get("From", ""))
                        if not self._is_openai_sender(from_addr):
                            continue

                        # Extract verification code
                        body = self._get_text_body(msg)
                        code = self._extract_otp(body)
                        if code:
                            # Mark as read
                            mail.store(msg_id, "+FLAGS", "\\Seen")
                            self.update_status(True)
                            logger.info(f"IMAP successfully obtained verification code: {code}")
                            return code

                except imaplib.IMAP4.error as e:
                    logger.debug(f"IMAP search for mail failed: {e}")
                    # Try to reconnect
                    try:
                        mail.select("INBOX")
                    except Exception:
                        pass

                time.sleep(3)

        except Exception as e:
            logger.warning(f"IMAP connection/polling failed: {e}")
            self.update_status(False, str(e))
        finally:
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass

        return None

    def check_health(self) -> bool:
        """Try IMAP login and select inbox"""
        mail = None
        try:
            mail = self._connect()
            status, _ = mail.select("INBOX")
            return status == "OK"
        except Exception as e:
            logger.warning(f"IMAP health check failed: {e}")
            return False
        finally:
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass

    def list_emails(self, **kwargs) -> list:
        """IMAP single account mode, return to fixed address"""
        return [{"email": self.email_addr, "id": self.email_addr}]

    def delete_email(self, email_id: str) -> bool:
        """IMAP mode does not require deletion logic"""
        return True
