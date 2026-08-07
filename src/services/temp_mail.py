"""Temp-Mail email service implementation
Self-hosted Cloudflare Worker temporary email service
For API documentation, see plan/temp-mail.md"""

import re
import time
import json
import logging
from email import message_from_string
from email.header import decode_header, make_header
from email.message import Message
from email.policy import default as email_policy
from html import unescape
from typing import Optional, Dict, Any, List

from .base import BaseEmailService, EmailServiceError, EmailServiceType
from ..core.http_client import HTTPClient, RequestConfig
from ..config.constants import OTP_CODE_PATTERN


logger = logging.getLogger(__name__)


class TempMailService(BaseEmailService):
    """Temp-Mail email service
    Temporary email based on self-hosted Cloudflare Worker, admin-managed email
    No proxy, no requests library"""

    def __init__(self, config: Dict[str, Any] = None, name: str = None):
        """Initialize TempMail service

        Args:
            config: settings dict with the following keys:
                - base_url: Worker URL, such as https://mail.example.com (required)
                - admin_password: Admin password for the x-admin-auth header (required)
                - domain: email domain, such as example.com (required)
                - enable_prefix: Enable prefix (default: True)
                - timeout: request timeout, default 30
                - max_retries: Maximum number of retries, default 3
            name: service name"""
        super().__init__(EmailServiceType.TEMP_MAIL, name)

        required_keys = ["base_url", "admin_password", "domain"]
        missing_keys = [key for key in required_keys if not (config or {}).get(key)]
        if missing_keys:
            raise ValueError(f"Missing required settings: {missing_keys}")

        default_config = {
            "enable_prefix": True,
            "timeout": 30,
            "max_retries": 3,
        }
        self.config = {**default_config, **(config or {})}

        # Not using a proxy, proxy_url=None
        http_config = RequestConfig(
            timeout=self.config["timeout"],
            max_retries=self.config["max_retries"],
        )
        self.http_client = HTTPClient(proxy_url=None, config=http_config)

        # Email cache: email -> {jwt, address}
        self._email_cache: Dict[str, Dict[str, Any]] = {}

    def _decode_mime_header(self, value: str) -> str:
        """Decode MIME headers (RFC 2047 encoded subjects)."""
        if not value:
            return ""
        try:
            return str(make_header(decode_header(value)))
        except Exception:
            return value

    def _extract_body_from_message(self, message: Message) -> str:
        """Extracts the readable body from a MIME message object."""
        parts: List[str] = []

        if message.is_multipart():
            for part in message.walk():
                if part.get_content_maintype() == "multipart":
                    continue

                content_type = (part.get_content_type() or "").lower()
                if content_type not in ("text/plain", "text/html"):
                    continue

                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    text = payload.decode(charset, errors="replace") if payload else ""
                except Exception:
                    try:
                        text = part.get_content()
                    except Exception:
                        text = ""

                if content_type == "text/html":
                    text = re.sub(r"<[^>]+>", " ", text)
                parts.append(text)
        else:
            try:
                payload = message.get_payload(decode=True)
                charset = message.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace") if payload else ""
            except Exception:
                try:
                    body = message.get_content()
                except Exception:
                    body = str(message.get_payload() or "")

            if "html" in (message.get_content_type() or "").lower():
                body = re.sub(r"<[^>]+>", " ", body)
            parts.append(body)

        return unescape("\n".join(part for part in parts if part).strip())

    def _extract_mail_fields(self, mail: Dict[str, Any]) -> Dict[str, str]:
        """Extract email fields from either raw MIME or Worker response formats."""
        sender = str(
            mail.get("source")
            or mail.get("from")
            or mail.get("from_address")
            or mail.get("fromAddress")
            or ""
        ).strip()
        subject = str(mail.get("subject") or mail.get("title") or "").strip()
        body_text = str(
            mail.get("text")
            or mail.get("body")
            or mail.get("content")
            or mail.get("html")
            or ""
        ).strip()
        raw = str(mail.get("raw") or "").strip()

        if raw:
            try:
                message = message_from_string(raw, policy=email_policy)
                sender = sender or self._decode_mime_header(message.get("From", ""))
                subject = subject or self._decode_mime_header(message.get("Subject", ""))
                parsed_body = self._extract_body_from_message(message)
                if parsed_body:
                    body_text = f"{body_text}\n{parsed_body}".strip() if body_text else parsed_body
            except Exception as e:
                logger.debug(f"Failed to parse TempMail raw email: {e}")
                body_text = f"{body_text}\n{raw}".strip() if body_text else raw

        body_text = unescape(re.sub(r"<[^>]+>", " ", body_text))
        return {
            "sender": sender,
            "subject": subject,
            "body": body_text,
            "raw": raw,
        }

    def _admin_headers(self) -> Dict[str, str]:
        """Build admin request headers"""
        return {
            "x-admin-auth": self.config["admin_password"],
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _make_request(self, method: str, path: str, **kwargs) -> Any:
        """Send a request and return JSON data

        Args:
            method: HTTP method
            path: request path (starting with /)
            **kwargs: additional parameters passed to http_client.request

        Returns:
            Response JSON data

        Raises:
            EmailServiceError: Request failed"""
        base_url = self.config["base_url"].rstrip("/")
        url = f"{base_url}{path}"

        # Merge default admin headers
        kwargs.setdefault("headers", {})
        for k, v in self._admin_headers().items():
            kwargs["headers"].setdefault(k, v)

        try:
            response = self.http_client.request(method, url, **kwargs)

            if response.status_code >= 400:
                error_msg = f"Failed to make request: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data}"
                except Exception:
                    error_msg = f"{error_msg} - {response.text[:200]}"
                self.update_status(False, EmailServiceError(error_msg))
                raise EmailServiceError(error_msg)

            try:
                return response.json()
            except json.JSONDecodeError:
                return {"raw_response": response.text}

        except Exception as e:
            self.update_status(False, e)
            if isinstance(e, EmailServiceError):
                raise
            raise EmailServiceError(f"Failed to make request: {method} {path} - {e}")

    def create_email(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create temporary email address via admin API

        Returns:
            Dictionary containing email data:
            - email: email address
            - jwt: user-level JWT token
            - service_id: same as email (used as identifier)"""
        import random
        import string

        # Generate random email name
        letters = ''.join(random.choices(string.ascii_lowercase, k=5))
        digits = ''.join(random.choices(string.digits, k=random.randint(1, 3)))
        suffix = ''.join(random.choices(string.ascii_lowercase, k=random.randint(1, 3)))
        name = letters + digits + suffix

        domain = self.config["domain"]
        enable_prefix = self.config.get("enable_prefix", True)

        body = {
            "enablePrefix": enable_prefix,
            "name": name,
            "domain": domain,
        }

        try:
            response = self._make_request("POST", "/admin/new_address", json=body)

            address = response.get("address", "").strip()
            jwt = response.get("jwt", "").strip()

            if not address:
                raise EmailServiceError(f"API response is incomplete: {response}")

            email_info = {
                "email": address,
                "jwt": jwt,
                "service_id": address,
                "id": address,
                "created_at": time.time(),
            }

            # Cache JWT for use when retrieving OTPs
            self._email_cache[address] = email_info

            logger.info(f"TempMail email address created: {address}")
            self.update_status(True)
            return email_info

        except Exception as e:
            self.update_status(False, e)
            if isinstance(e, EmailServiceError):
                raise
            raise EmailServiceError(f"Failed to create email address: {e}")

    def get_verification_code(
        self,
        email: str,
        email_id: str = None,
        timeout: int = 120,
        pattern: str = OTP_CODE_PATTERN,
        otp_sent_at: Optional[float] = None,
    ) -> Optional[str]:
        """Get OTP from TempMail email

        Args:
            email: email address
            email_id: Unused, reserved for API compatibility
            timeout: timeout (seconds)
            pattern: OTP regex pattern
            otp_sent_at: OTP sent timestamp (not used yet)

        Returns:
            OTP string, or None on timeout"""
        logger.info(f"Retrieving OTP from TempMail address {email}...")

        start_time = time.time()
        seen_mail_ids: set = set()

        # Prefer user-level JWT and fall back to admin API
        cached = self._email_cache.get(email, {})
        jwt = cached.get("jwt")

        while time.time() - start_time < timeout:
            try:
                if jwt:
                    response = self._make_request(
                        "GET",
                        "/user_api/mails",
                        params={"limit": 20, "offset": 0},
                        headers={"x-user-token": jwt, "Content-Type": "application/json", "Accept": "application/json"},
                    )
                else:
                    response = self._make_request(
                        "GET",
                        "/admin/mails",
                        params={"limit": 20, "offset": 0, "address": email},
                    )

                # /user_api/mails and /admin/mails return the same format: {"results": [...], "total": N}
                mails = response.get("results", [])
                if not isinstance(mails, list):
                    time.sleep(3)
                    continue

                for mail in mails:
                    mail_id = mail.get("id")
                    if not mail_id or mail_id in seen_mail_ids:
                        continue

                    seen_mail_ids.add(mail_id)

                    parsed = self._extract_mail_fields(mail)
                    sender = parsed["sender"].lower()
                    subject = parsed["subject"]
                    body_text = parsed["body"]
                    raw_text = parsed["raw"]
                    content = f"{sender}\n{subject}\n{body_text}\n{raw_text}".strip()

                    # Only handle OpenAI emails
                    if "openai" not in sender and "openai" not in content.lower():
                        continue

                    match = re.search(pattern, content)
                    if match:
                        code = match.group(1)
                        logger.info(f"OTP found from TempMail email {email}: {code}")
                        self.update_status(True)
                        return code

            except Exception as e:
                logger.debug(f"Error checking TempMail: {e}")

            time.sleep(3)

        logger.warning(f"Timeout waiting for TempMail OTP: {email}")
        return None

    def list_emails(self, limit: int = 100, offset: int = 0, **kwargs) -> List[Dict[str, Any]]:
        """List emails

        Args:
            limit: max results
            offset: pagination offset
            **kwargs: additional query parameters, forwarded to the admin API

        Returns:
            Email list"""
        params = {
            "limit": limit,
            "offset": offset,
        }
        params.update({k: v for k, v in kwargs.items() if v is not None})

        try:
            response = self._make_request("GET", "/admin/mails", params=params)
            mails = response.get("results", [])
            if not isinstance(mails, list):
                raise EmailServiceError(f"API response format error: {response}")

            emails: List[Dict[str, Any]] = []
            for mail in mails:
                address = (mail.get("address") or "").strip()
                mail_id = mail.get("id") or address
                email_info = {
                    "id": mail_id,
                    "service_id": mail_id,
                    "email": address,
                    "subject": mail.get("subject"),
                    "from": mail.get("source"),
                    "created_at": mail.get("createdAt") or mail.get("created_at"),
                    "raw_data": mail,
                }
                emails.append(email_info)

                if address:
                    cached = self._email_cache.get(address, {})
                    self._email_cache[address] = {**cached, **email_info}

            self.update_status(True)
            return emails
        except Exception as e:
            logger.warning(f"Failed to list TempMail emails: {e}")
            self.update_status(False, e)
            return list(self._email_cache.values())

    def delete_email(self, email_id: str) -> bool:
        """Delete email address

        Note:
            The TempMail admin API does not expose a delete-address endpoint.
            This stub satisfies the unified API contract and prevents service instantiation failures."""
        removed = False
        emails_to_delete = []

        for address, info in self._email_cache.items():
            candidate_ids = {
                address,
                info.get("id"),
                info.get("service_id"),
            }
            if email_id in candidate_ids:
                emails_to_delete.append(address)

        for address in emails_to_delete:
            self._email_cache.pop(address, None)
            removed = True

        if removed:
            logger.info(f"Email removed from TempMail cache: {email_id}")
            self.update_status(True)
        else:
            logger.info(f"Email not found in TempMail cache: {email_id}")

        return removed

    def check_health(self) -> bool:
        """Check service health status"""
        try:
            self._make_request(
                "GET",
                "/admin/mails",
                params={"limit": 1, "offset": 0},
            )
            self.update_status(True)
            return True
        except Exception as e:
            logger.warning(f"TempMail health check failed: {e}")
            self.update_status(False, e)
            return False
