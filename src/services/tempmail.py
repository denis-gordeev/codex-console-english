"""
Tempmail.lol email service implementation
"""

import re
import time
import logging
from typing import Optional, Dict, Any, List
import json

from curl_cffi import requests as cffi_requests

from .base import BaseEmailService, EmailServiceError, EmailServiceType
from ..core.http_client import HTTPClient, RequestConfig
from ..config.constants import OTP_CODE_PATTERN


logger = logging.getLogger(__name__)


class TempmailService(BaseEmailService):
    """
    Tempmail.lol Email Service
    Based on Tempmail.lol API v2
    """

    def __init__(self, config: Dict[str, Any] = None, name: str = None):
        """
        Initialize Tempmail service

        Args:
            config: configuration dictionary with the following keys:
                - base_url: API base address (default: https://api.tempmail.lol/v2)
                - timeout: request timeout (default: 30)
                - max_retries: Maximum number of retries (default: 3)
                - proxy_url: proxy URL
            name: service name
        """
        super().__init__(EmailServiceType.TEMPMAIL, name)

        # Default configuration
        default_config = {
            "base_url": "https://api.tempmail.lol/v2",
            "timeout": 30,
            "max_retries": 3,
            "proxy_url": None,
        }

        self.config = {**default_config, **(config or {})}

        # Create HTTP client
        http_config = RequestConfig(
            timeout=self.config["timeout"],
            max_retries=self.config["max_retries"],
        )
        self.http_client = HTTPClient(
            proxy_url=self.config.get("proxy_url"),
            config=http_config
        )

        # State variables
        self._email_cache: Dict[str, Dict[str, Any]] = {}
        self._last_check_time: float = 0

    def create_email(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a new temporary email address

        Args:
            config: Configuration options (Tempmail.lol does not support custom configuration)

        Returns:
            Dictionary containing email data:
            - email: email address
            - service_id: email token
            - token: email token (same as service_id)
            - created_at: creation timestamp
        """
        try:
            # Send create request
            response = self.http_client.post(
                f"{self.config['base_url']}/inbox/create",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={}
            )

            if response.status_code not in (200, 201):
                self.update_status(False, EmailServiceError(f"Request failed, status code: {response.status_code}"))
                raise EmailServiceError(f"Tempmail.lol request failed, status code: {response.status_code}")

            data = response.json()
            email = str(data.get("address", "")).strip()
            token = str(data.get("token", "")).strip()

            if not email or not token:
                self.update_status(False, EmailServiceError("Response data is incomplete"))
                raise EmailServiceError("Tempmail.lol returned incomplete data")

            # Cache email data
            email_info = {
                "email": email,
                "service_id": token,
                "token": token,
                "created_at": time.time(),
            }
            self._email_cache[email] = email_info

            logger.info(f"Tempmail.lol email address created: {email}")
            self.update_status(True)
            return email_info

        except Exception as e:
            self.update_status(False, e)
            if isinstance(e, EmailServiceError):
                raise
            raise EmailServiceError(f"Failed to create Tempmail.lol email address: {e}")

    def get_verification_code(
        self,
        email: str,
        email_id: str = None,
        timeout: int = 120,
        pattern: str = OTP_CODE_PATTERN,
        otp_sent_at: Optional[float] = None,
    ) -> Optional[str]:
        """
        Get OTP from Tempmail.lol

        Args:
            email: email address
            email_id: Email token (if not provided, search from cache)
            timeout: timeout (seconds)
            pattern: OTP regex pattern
            otp_sent_at: OTP sending timestamp (Tempmail service does not use this parameter yet)

        Returns:
            OTP string, or None on timeout / not found
        """
        token = email_id
        if not token:
            # Find token from cache
            if email in self._email_cache:
                token = self._email_cache[email].get("token")
            else:
                logger.warning(f"Token for email {email} not found; cannot retrieve OTP")
                return None

        if not token:
            logger.warning(f"Email address {email} has no token; cannot retrieve OTP")
            return None

        logger.info(f"Waiting for OTP for {email}...")

        start_time = time.time()
        seen_ids = set()

        while time.time() - start_time < timeout:
            try:
                # Get email list
                response = self.http_client.get(
                    f"{self.config['base_url']}/inbox",
                    params={"token": token},
                    headers={"Accept": "application/json"}
                )

                if response.status_code != 200:
                    time.sleep(3)
                    continue

                data = response.json()

                # Check if the inbox has expired
                if data is None or (isinstance(data, dict) and not data):
                    logger.warning(f"Email {email} has expired")
                    return None

                email_list = data.get("emails", []) if isinstance(data, dict) else []

                if not isinstance(email_list, list):
                    time.sleep(3)
                    continue

                for msg in email_list:
                    if not isinstance(msg, dict):
                        continue

                    # Use date as unique identifier
                    msg_date = msg.get("date", 0)
                    if not msg_date or msg_date in seen_ids:
                        continue
                    seen_ids.add(msg_date)

                    sender = str(msg.get("from", "")).lower()
                    subject = str(msg.get("subject", ""))
                    body = str(msg.get("body", ""))
                    html = str(msg.get("html") or "")

                    content = "\n".join([sender, subject, body, html])

                    # Check if it is an OpenAI email
                    if "openai" not in sender and "openai" not in content.lower():
                        continue

                    # Extract OTP
                    match = re.search(pattern, content)
                    if match:
                        code = match.group(1)
                        logger.info(f"OTP found: {code}")
                        self.update_status(True)
                        return code

            except Exception as e:
                logger.debug(f"Error checking email: {e}")

            # Wait for some time and check again
            time.sleep(3)

        logger.warning(f"Timed out waiting for OTP: {email}")
        return None

    def list_emails(self, **kwargs) -> List[Dict[str, Any]]:
        """
        List all cached emails

        Note:
            Tempmail.lol API does not support listing all emails; cached emails are returned instead.
        """
        return list(self._email_cache.values())

    def delete_email(self, email_id: str) -> bool:
        """
        Delete email address

        Note:
            Tempmail.lol API does not support deleting email addresses; the entry is removed from cache instead.
        """
        # Find and remove from cache
        emails_to_delete = []
        for email, info in self._email_cache.items():
            if info.get("token") == email_id:
                emails_to_delete.append(email)

        for email in emails_to_delete:
            del self._email_cache[email]
            logger.info(f"Remove email from cache: {email}")

        return len(emails_to_delete) > 0

    def check_health(self) -> bool:
        """Check if the Tempmail.lol service is reachable"""
        try:
            response = self.http_client.get(
                f"{self.config['base_url']}/inbox/create",
                timeout=10
            )
            # The service is considered available as long as it responds, regardless of status code
            self.update_status(True)
            return True
        except Exception as e:
            logger.warning(f"Tempmail.lol health check failed: {e}")
            self.update_status(False, e)
            return False

    def get_inbox(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get email inbox contents

        Args:
            token: email token

        Returns:
            Inbox data
        """
        try:
            response = self.http_client.get(
                f"{self.config['base_url']}/inbox",
                params={"token": token},
                headers={"Accept": "application/json"}
            )

            if response.status_code != 200:
                return None

            return response.json()
        except Exception as e:
            logger.error(f"Failed to get inbox: {e}")
            return None

    def wait_for_verification_code_with_callback(
        self,
        email: str,
        token: str,
        callback: callable = None,
        timeout: int = 120
    ) -> Optional[str]:
        """
        Wait for OTP with callback support

        Args:
            email: email address
            token: email token
            callback: callback function; receives current status updates
            timeout: Timeout (seconds)

        Returns:
            OTP or None
        """
        start_time = time.time()
        seen_ids = set()
        check_count = 0

        while time.time() - start_time < timeout:
            check_count += 1

            if callback:
                callback({
                    "status": "checking",
                    "email": email,
                    "check_count": check_count,
                    "elapsed_time": time.time() - start_time,
                })

            try:
                data = self.get_inbox(token)
                if not data:
                    time.sleep(3)
                    continue

                # Check if the inbox has expired
                if data is None or (isinstance(data, dict) and not data):
                    if callback:
                        callback({
                            "status": "expired",
                            "email": email,
                            "message": "Email has expired"
                        })
                    return None

                email_list = data.get("emails", []) if isinstance(data, dict) else []

                for msg in email_list:
                    msg_date = msg.get("date", 0)
                    if not msg_date or msg_date in seen_ids:
                        continue
                    seen_ids.add(msg_date)

                    sender = str(msg.get("from", "")).lower()
                    subject = str(msg.get("subject", ""))
                    body = str(msg.get("body", ""))
                    html = str(msg.get("html") or "")

                    content = "\n".join([sender, subject, body, html])

                    # Check if it is an OpenAI email
                    if "openai" not in sender and "openai" not in content.lower():
                        continue

                    # Extract OTP
                    match = re.search(OTP_CODE_PATTERN, content)
                    if match:
                        code = match.group(1)
                        if callback:
                            callback({
                                "status": "found",
                                "email": email,
                                "code": code,
                                "message": "OTP found"
                            })
                        return code

                if callback and check_count % 5 == 0:
                    callback({
                        "status": "waiting",
                        "email": email,
                        "check_count": check_count,
                        "message": f"Checked {len(seen_ids)} emails, waiting for OTP..."
                    })

            except Exception as e:
                logger.debug(f"Error checking email: {e}")
                if callback:
                    callback({
                        "status": "error",
                        "email": email,
                        "error": str(e),
                        "message": "An error occurred while checking mail"
                    })

            time.sleep(3)

        if callback:
            callback({
                "status": "timeout",
                "email": email,
                "message": "Timeout waiting for OTP"
            })
        return None
