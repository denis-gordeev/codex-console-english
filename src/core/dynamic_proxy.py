"""Dynamic proxy acquisition module
Supports obtaining dynamic proxy URL through external API"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def fetch_dynamic_proxy(api_url: str, api_key: str = "", api_key_header: str = "X-API-Key", result_field: str = "") -> Optional[str]:
    """Get proxy URL from proxy API

    Args:
        api_url: proxy API address, the response should be the proxy URL string or JSON containing the proxy URL
        api_key: API key (optional)
        api_key_header: API key request header name
        result_field: Extract the field path of the proxy URL from the JSON response. It supports dot separation (such as "data.proxy"). If left blank, the original response text will be used.

    Returns:
        Proxy URL string (such as http://user:pass@host:port), returns None on failure"""
    try:
        from curl_cffi import requests as cffi_requests

        headers = {}
        if api_key:
            headers[api_key_header] = api_key

        response = cffi_requests.get(
            api_url,
            headers=headers,
            timeout=10,
            impersonate="chrome110"
        )

        if response.status_code != 200:
            logger.warning(f"Dynamic proxy API returns error status code: {response.status_code}")
            return None

        text = response.text.strip()

        # Try to parse JSON
        if result_field or text.startswith("{") or text.startswith("["):
            try:
                import json
                data = json.loads(text)
                if result_field:
                    # Extract layer by layer according to point number path
                    for key in result_field.split("."):
                        if isinstance(data, dict):
                            data = data.get(key)
                        elif isinstance(data, list) and key.isdigit():
                            data = data[int(key)]
                        else:
                            data = None
                        if data is None:
                            break
                    proxy_url = str(data).strip() if data is not None else None
                else:
                    # No specified field, try common key names
                    for key in ("proxy", "url", "proxy_url", "data", "ip"):
                        val = data.get(key) if isinstance(data, dict) else None
                        if val:
                            proxy_url = str(val).strip()
                            break
                    else:
                        proxy_url = text
            except (ValueError, AttributeError):
                proxy_url = text
        else:
            proxy_url = text

        if not proxy_url:
            logger.warning("Dynamic proxy API returns empty proxy URL")
            return None

        # If no protocol header is included, http:// is added by default.
        if not re.match(r'^(http|socks5)://', proxy_url):
            proxy_url = "http://" + proxy_url

        logger.info(f"Dynamic proxy acquisition successful: {proxy_url[:40]}..." if len(proxy_url) > 40 else f"Dynamic proxy acquisition successful: {proxy_url}")
        return proxy_url

    except Exception as e:
        logger.error(f"Failed to obtain dynamic proxy: {e}")
        return None


def get_proxy_url_for_task() -> Optional[str]:
    """Get the proxy URL for the registration task.
    Dynamic proxies are used in preference if enabled, otherwise static proxy configurations are used.

    Returns:
        Proxy URL or None"""
    from ..config.settings import get_settings
    settings = get_settings()

    # Prefer using dynamic proxies
    if settings.proxy_dynamic_enabled and settings.proxy_dynamic_api_url:
        api_key = settings.proxy_dynamic_api_key.get_secret_value() if settings.proxy_dynamic_api_key else ""
        proxy_url = fetch_dynamic_proxy(
            api_url=settings.proxy_dynamic_api_url,
            api_key=api_key,
            api_key_header=settings.proxy_dynamic_api_key_header,
            result_field=settings.proxy_dynamic_result_field,
        )
        if proxy_url:
            return proxy_url
        logger.warning("Failed to obtain the dynamic proxy and fell back to the static proxy.")

    # Use static proxy
    return settings.proxy_url
