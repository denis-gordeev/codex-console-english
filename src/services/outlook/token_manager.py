"""Token manager with endpoint selection and in-memory caching."""

import json
import logging
import threading
import time
from typing import Dict, Optional, Any

from curl_cffi import requests as _requests

from .base import ProviderType, TokenEndpoint, TokenInfo
from .account import OutlookAccount


logger = logging.getLogger(__name__)


# Scope configuration for each provider.
PROVIDER_SCOPES = {
    ProviderType.IMAP_OLD: "",  # Legacy IMAP does not require a dedicated scope
    ProviderType.IMAP_NEW: "https://outlook.office.com/IMAP.AccessAsUser.All offline_access",
    ProviderType.GRAPH_API: "https://graph.microsoft.com/.default",
}

# Token endpoints for each provider.
PROVIDER_TOKEN_URLS = {
    ProviderType.IMAP_OLD: TokenEndpoint.LIVE.value,
    ProviderType.IMAP_NEW: TokenEndpoint.CONSUMERS.value,
    ProviderType.GRAPH_API: TokenEndpoint.COMMON.value,
}


class TokenManager:
    """Acquire and cache Outlook access tokens."""

    # Token cache: key = (email, provider_type) -> TokenInfo
    _token_cache: Dict[tuple, TokenInfo] = {}
    _cache_lock = threading.Lock()

    # Default timeout.
    DEFAULT_TIMEOUT = 30
    # Refresh slightly ahead of token expiry.
    REFRESH_BUFFER = 120

    def __init__(
        self,
        account: OutlookAccount,
        provider_type: ProviderType,
        proxy_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """Initialize the token manager.

        Args:
            account: Outlook account configuration.
            provider_type: Provider implementation to use.
            proxy_url: Optional proxy URL.
            timeout: HTTP request timeout in seconds.
        """
        self.account = account
        self.provider_type = provider_type
        self.proxy_url = proxy_url
        self.timeout = timeout

        # Resolve the endpoint and scope for the selected provider.
        self.token_url = PROVIDER_TOKEN_URLS.get(provider_type, TokenEndpoint.LIVE.value)
        self.scope = PROVIDER_SCOPES.get(provider_type, "")

    def get_cached_token(self) -> Optional[TokenInfo]:
        """Return a non-expired cached token when available."""
        cache_key = (self.account.email.lower(), self.provider_type)
        with self._cache_lock:
            token = self._token_cache.get(cache_key)
            if token and not token.is_expired(self.REFRESH_BUFFER):
                return token
        return None

    def set_cached_token(self, token: TokenInfo):
        """Store a token in the shared cache."""
        cache_key = (self.account.email.lower(), self.provider_type)
        with self._cache_lock:
            self._token_cache[cache_key] = token

    def clear_cache(self):
        """Clear the cached token for this account and provider."""
        cache_key = (self.account.email.lower(), self.provider_type)
        with self._cache_lock:
            self._token_cache.pop(cache_key, None)

    def get_access_token(self, force_refresh: bool = False) -> Optional[str]:
        """Return an access token.

        Args:
            force_refresh: Whether to bypass the cache and refresh immediately.

        Returns:
            Access token string, or `None` on failure.
        """
        # Check the cache first.
        if not force_refresh:
            cached = self.get_cached_token()
            if cached:
                logger.debug(f"[{self.account.email}] Using cached token ({self.provider_type.value})")
                return cached.access_token

        # Refresh the token when the cache misses or refresh is forced.
        try:
            token = self._refresh_token()
            if token:
                self.set_cached_token(token)
                return token.access_token
        except Exception as e:
            logger.error(f"[{self.account.email}] Failed to obtain Token ({self.provider_type.value}): {e}")

        return None

    def _refresh_token(self) -> Optional[TokenInfo]:
        """Refresh the access token using the stored refresh token.

        Returns:
            Token metadata, or `None` on failure.
        """
        if not self.account.client_id or not self.account.refresh_token:
            raise ValueError("Missing client_id or refresh_token")

        logger.debug(f"[{self.account.email}] Refreshing token ({self.provider_type.value})...")
        logger.debug(f"[{self.account.email}] Token URL: {self.token_url}")

        # Build the request body.
        data = {
            "client_id": self.account.client_id,
            "refresh_token": self.account.refresh_token,
            "grant_type": "refresh_token",
        }

        # Add the provider scope when required.
        if self.scope:
            data["scope"] = self.scope

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        proxies = None
        if self.proxy_url:
            proxies = {"http": self.proxy_url, "https": self.proxy_url}

        try:
            resp = _requests.post(
                self.token_url,
                data=data,
                headers=headers,
                proxies=proxies,
                timeout=self.timeout,
                impersonate="chrome110",
            )

            if resp.status_code != 200:
                error_body = resp.text
                logger.error(f"[{self.account.email}] Token refresh failed: HTTP {resp.status_code}")
                logger.debug(f"[{self.account.email}] Error response: {error_body[:500]}")

                if "service abuse" in error_body.lower():
                    logger.warning(f"[{self.account.email}] Account may be banned")
                elif "invalid_grant" in error_body.lower():
                    logger.warning(f"[{self.account.email}] Refresh token has expired")

                return None

            response_data = resp.json()

            # Parse the response.
            token = TokenInfo.from_response(response_data, self.scope)
            logger.info(
                f"[{self.account.email}] Token refreshed successfully ({self.provider_type.value}), "
                f"valid for {int(token.expires_at - time.time())} seconds"
            )
            return token

        except json.JSONDecodeError as e:
            logger.error(f"[{self.account.email}] JSON parsing error: {e}")
            return None

        except Exception as e:
            logger.error(f"[{self.account.email}] Unknown error: {e}")
            return None

    @classmethod
    def clear_all_cache(cls):
        """Clear the shared token cache."""
        with cls._cache_lock:
            cls._token_cache.clear()
            logger.info("All token caches cleared")

    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        """Return token cache statistics."""
        with cls._cache_lock:
            return {
                "cache_size": len(cls._token_cache),
                "entries": [
                    {
                        "email": key[0],
                        "provider": key[1].value,
                    }
                    for key in cls._token_cache.keys()
                ],
            }


def create_token_manager(
    account: OutlookAccount,
    provider_type: ProviderType,
    proxy_url: Optional[str] = None,
    timeout: int = TokenManager.DEFAULT_TIMEOUT,
) -> TokenManager:
    """Create a token manager instance.

    Args:
        account: Outlook account configuration.
        provider_type: Provider implementation to use.
        proxy_url: Optional proxy URL.
        timeout: HTTP request timeout in seconds.

    Returns:
        Configured `TokenManager` instance.
    """
    return TokenManager(account, provider_type, proxy_url, timeout)
