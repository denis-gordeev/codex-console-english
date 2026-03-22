"""Implementation of custom domain name mailbox service
Based on the REST API interface in email.md"""

import re
import time
import json
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

from .base import BaseEmailService, EmailServiceError, EmailServiceType
from ..core.http_client import HTTPClient, RequestConfig
from ..config.constants import OTP_CODE_PATTERN


logger = logging.getLogger(__name__)


class MeoMailEmailService(BaseEmailService):
    """Custom domain name email service
    Based on REST API interface"""

    def __init__(self, config: Dict[str, Any] = None, name: str = None):
        """Initialize custom domain name mailbox service

        Args:
            config: configuration dictionary, supports the following keys:
                - base_url: API base address (required)
                - api_key: API key (required)
                - api_key_header: API key request header name (default: X-API-Key)
                - timeout: request timeout (default: 30)
                - max_retries: Maximum number of retries (default: 3)
                - proxy_url: proxy URL
                - default_domain: default domain name
                - default_expiry: default expiration time (milliseconds)
            name: service name"""
        super().__init__(EmailServiceType.MOE_MAIL, name)

        # Required configuration check
        required_keys = ["base_url", "api_key"]
        missing_keys = [key for key in required_keys if key not in (config or {})]

        if missing_keys:
            raise ValueError(f"Missing required configuration: {missing_keys}")

        # Default configuration
        default_config = {
            "base_url": "",
            "api_key": "",
            "api_key_header": "X-API-Key",
            "timeout": 30,
            "max_retries": 3,
            "proxy_url": None,
            "default_domain": None,
            "default_expiry": 3600000,  # 1 hour
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

        # state variables
        self._emails_cache: Dict[str, Dict[str, Any]] = {}
        self._last_config_check: float = 0
        self._cached_config: Optional[Dict[str, Any]] = None

    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers"""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # Add API key
        api_key_header = self.config.get("api_key_header", "X-API-Key")
        headers[api_key_header] = self.config["api_key"]

        return headers

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Send API request

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: request parameters

        Returns:
            Respond to JSON data

        Raises:
            EmailServiceError: Request failed"""
        url = urljoin(self.config["base_url"], endpoint)

        # Add default request header
        kwargs.setdefault("headers", {})
        kwargs["headers"].update(self._get_headers())

        try:
            # Disable automatic redirection for POST requests and handle them manually to keep the POST method (to avoid being converted to GET when HTTP→HTTPS redirects)
            if method.upper() == "POST":
                kwargs["allow_redirects"] = False
                response = self.http_client.request(method, url, **kwargs)
                # Handle redirects
                max_redirects = 5
                redirect_count = 0
                while response.status_code in (301, 302, 303, 307, 308) and redirect_count < max_redirects:
                    location = response.headers.get("Location", "")
                    if not location:
                        break
                    import urllib.parse as _urlparse
                    redirect_url = _urlparse.urljoin(url, location)
                    # 307/308 remain POST, the rest (301/302/303) convert to GET
                    if response.status_code in (307, 308):
                        redirect_method = method
                        redirect_kwargs = kwargs
                    else:
                        redirect_method = "GET"
                        # GET does not pass body
                        redirect_kwargs = {k: v for k, v in kwargs.items() if k not in ("json", "data")}
                    response = self.http_client.request(redirect_method, redirect_url, **redirect_kwargs)
                    url = redirect_url
                    redirect_count += 1
            else:
                response = self.http_client.request(method, url, **kwargs)

            if response.status_code >= 400:
                error_msg = f"API request failed: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data}"
                except:
                    error_msg = f"{error_msg} - {response.text[:200]}"

                self.update_status(False, EmailServiceError(error_msg))
                raise EmailServiceError(error_msg)

            # Parse response
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"raw_response": response.text}

        except Exception as e:
            self.update_status(False, e)
            if isinstance(e, EmailServiceError):
                raise
            raise EmailServiceError(f"API request failed: {method} {endpoint} - {e}")

    def get_config(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get system configuration

        Args:
            force_refresh: whether to force cache refresh

        Returns:
            Configuration information"""
        # Check cache
        if not force_refresh and self._cached_config and time.time() - self._last_config_check < 300:
            return self._cached_config

        try:
            response = self._make_request("GET", "/api/config")
            self._cached_config = response
            self._last_config_check = time.time()
            self.update_status(True)
            return response
        except Exception as e:
            logger.warning(f"Failed to get configuration: {e}")
            return {}

    def create_email(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create temporary mailbox

        Args:
            config: configuration parameters:
                - name: email prefix (optional)
                - expiryTime: validity period (milliseconds) (optional)
                - domain: email domain name (optional)

        Returns:
            Dictionary containing email information:
            - email: email address
            - service_id: Email ID
            - id: Email ID (same as service_id)
            - expiry: expiration time information"""
        # Get default configuration
        sys_config = self.get_config()
        default_domain = self.config.get("default_domain")
        if not default_domain and sys_config.get("emailDomains"):
            # Use the first domain name configured by the system
            domains = sys_config["emailDomains"].split(",")
            default_domain = domains[0].strip() if domains else None

        # Build request parameters
        request_config = config or {}
        create_data = {
            "name": request_config.get("name", ""),
            "expiryTime": request_config.get("expiryTime", self.config.get("default_expiry", 3600000)),
            "domain": request_config.get("domain", default_domain),
        }

        # Remove null values
        create_data = {k: v for k, v in create_data.items() if v is not None and v != ""}

        try:
            response = self._make_request("POST", "/api/emails/generate", json=create_data)

            email = response.get("email", "").strip()
            email_id = response.get("id", "").strip()

            if not email or not email_id:
                raise EmailServiceError("API returns incomplete data")

            email_info = {
                "email": email,
                "service_id": email_id,
                "id": email_id,
                "created_at": time.time(),
                "expiry": create_data.get("expiryTime"),
                "domain": create_data.get("domain"),
                "raw_response": response,
            }

            # Caching email information
            self._emails_cache[email_id] = email_info

            logger.info(f"Successfully created custom domain name email: {email} (ID: {email_id})")
            self.update_status(True)
            return email_info

        except Exception as e:
            self.update_status(False, e)
            if isinstance(e, EmailServiceError):
                raise
            raise EmailServiceError(f"Failed to create mailbox: {e}")

    def get_verification_code(
        self,
        email: str,
        email_id: str = None,
        timeout: int = 120,
        pattern: str = OTP_CODE_PATTERN,
        otp_sent_at: Optional[float] = None,
    ) -> Optional[str]:
        """Get verification code from custom domain name email

        Args:
            email: email address
            email_id: Email ID (if not provided, search from cache)
            timeout: timeout (seconds)
            pattern: verification code regular expression
            otp_sent_at: OTP sending timestamp (custom domain name service does not use this parameter yet)

        Returns:
            Verification code string, returns None if timeout or not found"""
        # Find email ID
        target_email_id = email_id
        if not target_email_id:
            # Find from cache
            for eid, info in self._emails_cache.items():
                if info.get("email") == email:
                    target_email_id = eid
                    break

        if not target_email_id:
            logger.warning(f"The ID of the email address {email} was not found and the verification code cannot be obtained.")
            return None

        logger.info(f"Obtaining verification code from custom domain name email {email}...")

        start_time = time.time()
        seen_message_ids = set()

        while time.time() - start_time < timeout:
            try:
                # Get mailing list
                response = self._make_request("GET", f"/api/emails/{target_email_id}")

                messages = response.get("messages", [])
                if not isinstance(messages, list):
                    time.sleep(3)
                    continue

                for message in messages:
                    message_id = message.get("id")
                    if not message_id or message_id in seen_message_ids:
                        continue

                    seen_message_ids.add(message_id)

                    # Check if it is the target email
                    sender = str(message.get("from_address", "")).lower()
                    subject = str(message.get("subject", ""))

                    # Get email content
                    message_content = self._get_message_content(target_email_id, message_id)
                    if not message_content:
                        continue

                    content = f"{sender} {subject} {message_content}"

                    # Check if it is an OpenAI email
                    if "openai" not in sender and "openai" not in content.lower():
                        continue

                    # Extract verification code and filter out emails
                    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
                    match = re.search(pattern, re.sub(email_pattern, "", content))
                    if match:
                        code = match.group(1)
                        logger.info(f"Find the verification code from the custom domain name email {email}: {code}")
                        self.update_status(True)
                        return code

            except Exception as e:
                logger.debug(f"Error checking mail: {e}")

            # Wait for some time and check again
            time.sleep(3)

        logger.warning(f"Timeout waiting for verification code: {email}")
        return None

    def _get_message_content(self, email_id: str, message_id: str) -> Optional[str]:
        """Get email content"""
        try:
            response = self._make_request("GET", f"/api/emails/{email_id}/{message_id}")
            message = response.get("message", {})

            # Use plain text content first, HTML content second
            content = message.get("content", "")
            if not content:
                html = message.get("html", "")
                if html:
                    # Easily remove HTML tags
                    content = re.sub(r"<[^>]+>", " ", html)

            return content
        except Exception as e:
            logger.debug(f"Failed to get email content: {e}")
            return None

    def list_emails(self, cursor: str = None, **kwargs) -> List[Dict[str, Any]]:
        """List all emails

        Args:
            cursor: paging cursor
            **kwargs: other parameters

        Returns:
            Email list"""
        params = {}
        if cursor:
            params["cursor"] = cursor

        try:
            response = self._make_request("GET", "/api/emails", params=params)
            emails = response.get("emails", [])

            # Update cache
            for email_info in emails:
                email_id = email_info.get("id")
                if email_id:
                    self._emails_cache[email_id] = email_info

            self.update_status(True)
            return emails
        except Exception as e:
            logger.warning(f"Failed to list mailbox: {e}")
            self.update_status(False, e)
            return []

    def delete_email(self, email_id: str) -> bool:
        """Delete mailbox

        Args:
            email_id: Email ID

        Returns:
            Is deletion successful?"""
        try:
            response = self._make_request("DELETE", f"/api/emails/{email_id}")
            success = response.get("success", False)

            if success:
                # Remove from cache
                self._emails_cache.pop(email_id, None)
                logger.info(f"Email deleted successfully: {email_id}")
            else:
                logger.warning(f"Failed to delete mailbox: {email_id}")

            self.update_status(success)
            return success

        except Exception as e:
            logger.error(f"Failed to delete mailbox: {email_id} - {e}")
            self.update_status(False, e)
            return False

    def check_health(self) -> bool:
        """Check whether the custom domain name email service is available"""
        try:
            # Try to get configuration
            config = self.get_config(force_refresh=True)
            if config:
                logger.debug(f"The custom domain name mailbox service health check passed, configuration: {config.get('defaultRole', 'N/A')}")
                self.update_status(True)
                return True
            else:
                logger.warning("Custom domain name mailbox service health check failed: the obtained configuration is empty")
                self.update_status(False, EmailServiceError("Get configuration is empty"))
                return False
        except Exception as e:
            logger.warning(f"Custom domain name mailbox service health check failed: {e}")
            self.update_status(False, e)
            return False

    def get_email_messages(self, email_id: str, cursor: str = None) -> List[Dict[str, Any]]:
        """Get the mailing list in your mailbox

        Args:
            email_id: Email ID
            cursor: paging cursor

        Returns:
            mailing list"""
        params = {}
        if cursor:
            params["cursor"] = cursor

        try:
            response = self._make_request("GET", f"/api/emails/{email_id}", params=params)
            messages = response.get("messages", [])
            self.update_status(True)
            return messages
        except Exception as e:
            logger.error(f"Failed to get mailing list: {email_id} - {e}")
            self.update_status(False, e)
            return []

    def get_message_detail(self, email_id: str, message_id: str) -> Optional[Dict[str, Any]]:
        """Get email details

        Args:
            email_id: Email ID
            message_id: email ID

        Returns:
            Email details"""
        try:
            response = self._make_request("GET", f"/api/emails/{email_id}/{message_id}")
            message = response.get("message")
            self.update_status(True)
            return message
        except Exception as e:
            logger.error(f"Failed to get email details: {email_id}/{message_id} - {e}")
            self.update_status(False, e)
            return None

    def create_email_share(self, email_id: str, expires_in: int = 86400000) -> Optional[Dict[str, Any]]:
        """Create email sharing link

        Args:
            email_id: Email ID
            expires_in: validity period (milliseconds)

        Returns:
            share information"""
        try:
            response = self._make_request(
                "POST",
                f"/api/emails/{email_id}/share",
                json={"expiresIn": expires_in}
            )
            self.update_status(True)
            return response
        except Exception as e:
            logger.error(f"Failed to create email sharing link: {email_id} - {e}")
            self.update_status(False, e)
            return None

    def create_message_share(
        self,
        email_id: str,
        message_id: str,
        expires_in: int = 86400000
    ) -> Optional[Dict[str, Any]]:
        """Create email sharing link

        Args:
            email_id: Email ID
            message_id: email ID
            expires_in: validity period (milliseconds)

        Returns:
            share information"""
        try:
            response = self._make_request(
                "POST",
                f"/api/emails/{email_id}/messages/{message_id}/share",
                json={"expiresIn": expires_in}
            )
            self.update_status(True)
            return response
        except Exception as e:
            logger.error(f"Failed to create email sharing link: {email_id}/{message_id} - {e}")
            self.update_status(False, e)
            return None

    def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        config = self.get_config()
        return {
            "service_type": self.service_type.value,
            "name": self.name,
            "base_url": self.config["base_url"],
            "default_domain": self.config.get("default_domain"),
            "system_config": config,
            "cached_emails_count": len(self._emails_cache),
            "status": self.status.value,
        }