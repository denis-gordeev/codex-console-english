"""
Freemail email service implementation
Self-hosted Cloudflare Worker temporary email service (https://github.com/idinging/freemail)
"""

import re
import time
import logging
import random
import string
from typing import Optional, Dict, Any, List

from .base import BaseEmailService, EmailServiceError, EmailServiceType
from ..core.http_client import HTTPClient, RequestConfig
from ..config.constants import OTP_CODE_PATTERN

logger = logging.getLogger(__name__)


class FreemailService(BaseEmailService):
    """
    Freemail email service
    Temporary email based on self-hosted Cloudflare Worker
    """

    def __init__(self, config: Dict[str, Any] = None, name: str = None):
        """
        Initialize Freemail service

        Args:
            config: settings dict with the following keys:
                - base_url: Worker URL (required)
                - admin_token: Admin Token for JWT_TOKEN (required)
                - domain: email domain, such as example.com
                - timeout: request timeout, default 30
                - max_retries: Max retries, default 3
            name: service name
        """
        super().__init__(EmailServiceType.FREEMAIL, name)

        required_keys = ["base_url", "admin_token"]
        missing_keys = [key for key in required_keys if not (config or {}).get(key)]
        if missing_keys:
            raise ValueError(f"Missing required settings: {missing_keys}")

        default_config = {
            "timeout": 30,
            "max_retries": 3,
        }
        self.config = {**default_config, **(config or {})}
        self.config["base_url"] = self.config["base_url"].rstrip("/")

        http_config = RequestConfig(
            timeout=self.config["timeout"],
            max_retries=self.config["max_retries"],
        )
        self.http_client = HTTPClient(proxy_url=None, config=http_config)

        # Cache domain list
        self._domains = []

    def _get_headers(self) -> Dict[str, str]:
        """Build admin request headers"""
        return {
            "Authorization": f"Bearer {self.config['admin_token']}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _make_request(self, method: str, path: str, **kwargs) -> Any:
        """
        Send a request and return JSON data

        Args:
            method: HTTP method
            path: request path (starting with /)
            **kwargs: additional parameters passed to http_client.request

        Returns:
            Response JSON data

        Raises:
            EmailServiceError: Request failed
        """
        url = f"{self.config['base_url']}{path}"
        kwargs.setdefault("headers", {})
        kwargs["headers"].update(self._get_headers())

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
            except Exception:
                return {"raw_response": response.text}

        except Exception as e:
            self.update_status(False, e)
            if isinstance(e, EmailServiceError):
                raise
            raise EmailServiceError(f"Failed to make request: {method} {path} - {e}")

    def _ensure_domains(self):
        """Fetch and cache available domains"""
        if not self._domains:
            try:
                domains = self._make_request("GET", "/api/domains")
                if isinstance(domains, list):
                    self._domains = domains
            except Exception as e:
                logger.warning(f"Failed to fetch Freemail domain list: {e}")

    def create_email(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create temporary email address via API

        Returns:
            Dictionary containing email data:
            - email: email address
            - service_id: same as email (used as identifier)
        """
        self._ensure_domains()
        
        req_config = config or {}
        domain_index = 0
        target_domain = req_config.get("domain") or self.config.get("domain")
        
        if target_domain and self._domains:
            for i, d in enumerate(self._domains):
                if d == target_domain:
                    domain_index = i
                    break
                    
        prefix = req_config.get("name")
        try:
            if prefix:
                body = {
                    "local": prefix,
                    "domainIndex": domain_index
                }
                resp = self._make_request("POST", "/api/create", json=body)
            else:
                params = {"domainIndex": domain_index}
                length = req_config.get("length")
                if length:
                    params["length"] = length
                resp = self._make_request("GET", "/api/generate", params=params)

            email = resp.get("email")
            if not email:
                raise EmailServiceError(f"Failed to create email, no email returned: {resp}")

            email_info = {
                "email": email,
                "service_id": email,
                "id": email,
                "created_at": time.time(),
            }

            logger.info(f"Freemail email address created: {email}")
            self.update_status(True)
            return email_info

        except Exception as e:
            self.update_status(False, e)
            if isinstance(e, EmailServiceError):
                raise
            raise EmailServiceError(f"Failed to create email: {e}")

    def get_otp(
        self,
        email: str,
        email_id: str = None,
        timeout: int = 120,
        pattern: str = OTP_CODE_PATTERN,
        otp_sent_at: Optional[float] = None,
    ) -> Optional[str]:
        """
        Get OTP from Freemail email

        Args:
            email: email address
            email_id: Unused, reserved for API compatibility
            timeout: timeout (seconds)
            pattern: OTP regex pattern
            otp_sent_at: OTP sent timestamp (not used yet)

        Returns:
            OTP string, or None on timeout
        """
        logger.info(f"Retrieving OTP from Freemail address {email}...")

        start_time = time.time()
        seen_mail_ids: set = set()

        while time.time() - start_time < timeout:
            try:
                mails = self._make_request("GET", "/api/emails", params={"mailbox": email, "limit": 20})
                if not isinstance(mails, list):
                    time.sleep(3)
                    continue

                for mail in mails:
                    mail_id = mail.get("id")
                    if not mail_id or mail_id in seen_mail_ids:
                        continue

                    seen_mail_ids.add(mail_id)

                    sender = str(mail.get("sender", "")).lower()
                    subject = str(mail.get("subject", ""))
                    preview = str(mail.get("preview", ""))
                    
                    content = f"{sender}\n{subject}\n{preview}"
                    
                    if "openai" not in content.lower():
                        continue

                    # Try to use the OTP extracted by Freemail directly
                    v_code = mail.get("verification_code")
                    if v_code:
                        logger.info(f"Found OTP for Freemail email {email}: {v_code}")
                        self.update_status(True)
                        return v_code

                    # If not provided directly, match preview through regex pattern
                    match = re.search(pattern, content)
                    if match:
                        code = match.group(1)
                        logger.info(f"Found OTP for Freemail email {email}: {code}")
                        self.update_status(True)
                        return code

                    # If still not found, get email details for matching
                    try:
                        detail = self._make_request("GET", f"/api/email/{mail_id}")
                        full_content = str(detail.get("content", "")) + "\n" + str(detail.get("html_content", ""))
                        match = re.search(pattern, full_content)
                        if match:
                            code = match.group(1)
                            logger.info(f"Found OTP for Freemail email {email}: {code}")
                            self.update_status(True)
                            return code
                    except Exception as e:
                        logger.debug(f"Failed to fetch Freemail email details: {e}")

            except Exception as e:
                logger.debug(f"Error checking Freemail mail: {e}")

            time.sleep(3)

        logger.warning(f"Timeout waiting for Freemail OTP: {email}")
        return None

    def list_emails(self, **kwargs) -> List[Dict[str, Any]]:
        """
        List emails

        Args:
            **kwargs: additional query parameters

        Returns:
            Email list
        """
        try:
            params = {
                "limit": kwargs.get("limit", 100),
                "offset": kwargs.get("offset", 0)
            }
            resp = self._make_request("GET", "/api/mailboxes", params=params)
            
            emails = []
            if isinstance(resp, list):
                for mail in resp:
                    address = mail.get("address")
                    if address:
                        emails.append({
                            "id": address,
                            "service_id": address,
                            "email": address,
                            "created_at": mail.get("created_at"),
                            "raw_data": mail
                        })
            self.update_status(True)
            return emails
        except Exception as e:
            logger.warning(f"Failed to list Freemail emails: {e}")
            self.update_status(False, e)
            return []

    def delete_email(self, email_id: str) -> bool:
        """
        Delete email address
        """
        try:
            self._make_request("DELETE", "/api/mailboxes", params={"address": email_id})
            logger.info(f"Deleted Freemail email: {email_id}")
            self.update_status(True)
            return True
        except Exception as e:
            logger.warning(f"Failed to delete Freemail email address: {e}")
            self.update_status(False, e)
            return False

    def check_health(self) -> bool:
        """Check service health status"""
        try:
            self._make_request("GET", "/api/domains")
            self.update_status(True)
            return True
        except Exception as e:
            logger.warning(f"Freemail health check failed: {e}")
            self.update_status(False, e)
            return False
