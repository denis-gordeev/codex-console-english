"""
HTTP client encapsulation
HTTP request encapsulation based on curl_cffi, supporting proxy and error handling
"""

import time
import json
from typing import Optional, Dict, Any, Union, Tuple
from dataclasses import dataclass
import logging

from curl_cffi import requests as cffi_requests
from curl_cffi.requests import Session, Response

from ..config.constants import ERROR_MESSAGES
from ..config.settings import get_settings
from .openai.sentinel import SentinelPOWError, build_sentinel_pow_token


logger = logging.getLogger(__name__)


@dataclass
class RequestConfig:
    """HTTP request configuration"""
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    impersonate: str = "chrome"
    verify_ssl: bool = True
    follow_redirects: bool = True


class HTTPClientError(Exception):
    """HTTP client exception"""
    pass


class HTTPClient:
    """
    HTTP client encapsulation
    Supports proxies, retries, error handling and session management
    """

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        config: Optional[RequestConfig] = None,
        session: Optional[Session] = None
    ):
        """
        Initialize HTTP client

        Args:
            proxy_url: proxy URL, such as "http://127.0.0.1:7890"
            config: request configuration
            session: reusable session object
        """
        self.proxy_url = proxy_url
        self.config = config or RequestConfig()
        self._session = session

    @property
    def proxies(self) -> Optional[Dict[str, str]]:
        """Get proxy configuration"""
        if not self.proxy_url:
            return None
        return {
            "http": self.proxy_url,
            "https": self.proxy_url,
        }

    @property
    def session(self) -> Session:
        """Get the session object (singleton)"""
        if self._session is None:
            self._session = Session(
                proxies=self.proxies,
                impersonate=self.config.impersonate,
                verify=self.config.verify_ssl,
                timeout=self.config.timeout
            )
        return self._session

    def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Response:
        """
        Send HTTP request

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: request URL
            **kwargs: other request parameters

        Returns:
            Response object

        Raises:
            HTTPClientError: Request failed
        """
        # Set default parameters
        kwargs.setdefault("timeout", self.config.timeout)
        kwargs.setdefault("allow_redirects", self.config.follow_redirects)

        #Add proxy configuration
        if self.proxies and "proxies" not in kwargs:
            kwargs["proxies"] = self.proxies

        last_exception = None
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.request(method, url, **kwargs)

                # Check response status code
                if response.status_code >= 400:
                    logger.warning(
                        f"HTTP {response.status_code} for {method} {url}"
                        f" (attempt {attempt + 1}/{self.config.max_retries})"
                    )

                    # If it is a server error, try again
                    if response.status_code >= 500 and attempt < self.config.max_retries - 1:
                        time.sleep(self.config.retry_delay * (attempt + 1))
                        continue

                return response

            except (cffi_requests.RequestsError, ConnectionError, TimeoutError) as e:
                last_exception = e
                logger.warning(
                    f"Request failed: {method} {url} (attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )

                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    break

        raise HTTPClientError(
            f"The request failed, the maximum number of retries has been reached: {method} {url} - {last_exception}"
        )

    def get(self, url: str, **kwargs) -> Response:
        """Send GET request"""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, data: Any = None, json: Any = None, **kwargs) -> Response:
        """Send POST request"""
        return self.request("POST", url, data=data, json=json, **kwargs)

    def put(self, url: str, data: Any = None, json: Any = None, **kwargs) -> Response:
        """Send PUT request"""
        return self.request("PUT", url, data=data, json=json, **kwargs)

    def delete(self, url: str, **kwargs) -> Response:
        """Send DELETE request"""
        return self.request("DELETE", url, **kwargs)

    def head(self, url: str, **kwargs) -> Response:
        """Send HEAD request"""
        return self.request("HEAD", url, **kwargs)

    def options(self, url: str, **kwargs) -> Response:
        """Send OPTIONS request"""
        return self.request("OPTIONS", url, **kwargs)

    def patch(self, url: str, data: Any = None, json: Any = None, **kwargs) -> Response:
        """Send PATCH request"""
        return self.request("PATCH", url, data=data, json=json, **kwargs)

    def download_file(self, url: str, filepath: str, chunk_size: int = 8192) -> None:
        """
        Download file

        Args:
            url: file URL
            filepath: save path
            chunk_size: chunk size

        Raises:
            HTTPClientError: Download failed
        """
        try:
            response = self.get(url, stream=True)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)

        except Exception as e:
            raise HTTPClientError(f"Failed to download file: {url} - {e}")

    def check_proxy(self, test_url: str = "https://httpbin.org/ip") -> bool:
        """
        Check if proxy is available

        Args:
            test_url: test URL

        Returns:
            bool: whether the agent is available
        """
        if not self.proxy_url:
            return False

        try:
            response = self.get(test_url, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def close(self):
        """Close session"""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class OpenAIHTTPClient(HTTPClient):
    """
    OpenAI dedicated HTTP client
    Contains OpenAI API specific request methods
    """

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        config: Optional[RequestConfig] = None
    ):
        """
        Initialize the OpenAI HTTP client

        Args:
            proxy_url: proxy URL
            config: request configuration
        """
        super().__init__(proxy_url, config)

        # OpenAI specific default configuration
        if config is None:
            self.config.timeout = 30
            self.config.max_retries = 3

        #Default request header
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }

    def check_ip_location(self) -> Tuple[bool, Optional[str]]:
        """
        Check IP geolocation

        Returns:
            Tuple[whether supported, location information]
        """
        try:
            response = self.get("https://cloudflare.com/cdn-cgi/trace", timeout=10)
            trace_text = response.text

            # Parse location information
            import re
            loc_match = re.search(r"loc=([A-Z]+)", trace_text)
            loc = loc_match.group(1) if loc_match else None

            # Check if supported
            if loc in ["CN", "HK", "MO", "TW"]:
                return False, loc
            return True, loc

        except Exception as e:
            logger.error(f"Failed to check IP location: {e}")
            return False, None

    def send_openai_request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send an OpenAI API request

        Args:
            endpoint: API endpoint
            method: HTTP method
            data: form data
            json_data: JSON data
            headers: request headers
            **kwargs: other parameters

        Returns:
            Respond to JSON data

        Raises:
            HTTPClientError: Request failed
        """
        # Merge request headers
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)

        # Set Content-Type
        if json_data is not None and "Content-Type" not in request_headers:
            request_headers["Content-Type"] = "application/json"
        elif data is not None and "Content-Type" not in request_headers:
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"

        try:
            response = self.request(
                method,
                endpoint,
                data=data,
                json=json_data,
                headers=request_headers,
                **kwargs
            )

            # Check response status code
            response.raise_for_status()

            # Try to parse JSON
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"raw_response": response.text}

        except cffi_requests.RequestsError as e:
            raise HTTPClientError(f"OpenAI request failed: {endpoint} - {e}")

    def check_sentinel(self, did: str, proxies: Optional[Dict] = None) -> Optional[str]:
        """
        Check Sentinel interception

        Args:
            did: Device ID
            proxies: proxy configuration

        Returns:
            Sentinel token or None
        """
        from ..config.constants import OPENAI_API_ENDPOINTS

        try:
            pow_token = build_sentinel_pow_token(self.default_headers.get("User-Agent", ""))
            sen_req_body = json.dumps({
                "p": pow_token,
                "id": did,
                "flow": "authorize_continue",
            }, separators=(",", ":"))

            response = self.post(
                OPENAI_API_ENDPOINTS["sentinel"],
                headers={
                    "origin": "https://sentinel.openai.com",
                    "referer": "https://sentinel.openai.com/backend-api/sentinel/frame.html?sv=20260219f9f6",
                    "content-type": "text/plain;charset=UTF-8",
                },
                data=sen_req_body,
            )

            if response.status_code == 200:
                return response.json().get("token")
            else:
                logger.warning(f"Sentinel check failed: {response.status_code}")
                return None

        except SentinelPOWError as e:
            logger.error(f"Sentinel POW solution failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Sentinel check exception: {e}")
            return None


def create_http_client(
    proxy_url: Optional[str] = None,
    config: Optional[RequestConfig] = None
) -> HTTPClient:
    """
    Create an HTTP client factory function

    Args:
        proxy_url: proxy URL
        config: request configuration

    Returns:
        HTTPClient instance
    """
    return HTTPClient(proxy_url, config)


def create_openai_client(
    proxy_url: Optional[str] = None,
    config: Optional[RequestConfig] = None
) -> OpenAIHTTPClient:
    """
    Create OpenAI HTTP client factory function

    Args:
        proxy_url: proxy URL
        config: request configuration

    Returns:
        OpenAIHTTPClient instance
    """
    return OpenAIHTTPClient(proxy_url, config)
