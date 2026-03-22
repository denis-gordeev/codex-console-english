"""
Token refresh module
Supports two refresh methods: Session Token and OAuth Refresh Token
"""

import logging
import json
import time
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from curl_cffi import requests as cffi_requests

from ...config.settings import get_settings
from ...database.session import get_db
from ...database import crud
from ...database.models import Account

logger = logging.getLogger(__name__)


@dataclass
class TokenRefreshResult:
    """Token refresh results"""
    success: bool
    access_token: str = ""
    refresh_token: str = ""
    expires_at: Optional[datetime] = None
    error_message: str = ""


class TokenRefreshManager:
    """
    Token refresh manager
    Supports two refresh methods:
    1. Session Token refresh (priority)
    2. OAuth Refresh Token refresh
    """

    # OpenAI OAuth endpoint
    SESSION_URL = "https://chatgpt.com/api/auth/session"
    TOKEN_URL = "https://auth.openai.com/oauth/token"

    def __init__(self, proxy_url: Optional[str] = None):
        """
        Initialize Token refresh manager

        Args:
            proxy_url: proxy URL
        """
        self.proxy_url = proxy_url
        self.settings = get_settings()

    def _create_session(self) -> cffi_requests.Session:
        """Create HTTP session"""
        session = cffi_requests.Session(impersonate="chrome120", proxy=self.proxy_url)
        return session

    def refresh_by_session_token(self, session_token: str) -> TokenRefreshResult:
        """
        Refresh using Session Token

        Args:
            session_token: session token

        Returns:
            TokenRefreshResult: Refresh the result
        """
        result = TokenRefreshResult(success=False)

        try:
            session = self._create_session()

            # Set session cookie
            session.cookies.set(
                "__Secure-next-auth.session-token",
                session_token,
                domain=".chatgpt.com",
                path="/"
            )

            # Request session endpoint
            response = session.get(
                self.SESSION_URL,
                headers={
                    "accept": "application/json",
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                timeout=30
            )

            if response.status_code != 200:
                result.error_message = f"Session token refresh failed: HTTP {response.status_code}"
                logger.warning(result.error_message)
                return result

            data = response.json()

            #Extract access_token
            access_token = data.get("accessToken")
            if not access_token:
                result.error_message = "Session token refresh failed: accessToken not found"
                logger.warning(result.error_message)
                return result

            #Extract expiration time
            expires_at = None
            expires_str = data.get("expires")
            if expires_str:
                try:
                    expires_at = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                except:
                    pass

            result.success = True
            result.access_token = access_token
            result.expires_at = expires_at

            logger.info(f"Session token refreshed successfully, expiration time: {expires_at}")
            return result

        except Exception as e:
            result.error_message = f"Session token refresh exception: {str(e)}"
            logger.error(result.error_message)
            return result

    def refresh_by_oauth_token(
        self,
        refresh_token: str,
        client_id: Optional[str] = None
    ) -> TokenRefreshResult:
        """
        Refresh using OAuth Refresh Token

        Args:
            refresh_token: OAuth refresh token
            client_id: OAuth Client ID

        Returns:
            TokenRefreshResult: Refresh the result
        """
        result = TokenRefreshResult(success=False)

        try:
            session = self._create_session()

            # Use configured client_id or default value
            client_id = client_id or self.settings.openai_client_id

            # Build request body
            token_data = {
                "client_id": client_id,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "redirect_uri": self.settings.openai_redirect_uri
            }

            response = session.post(
                self.TOKEN_URL,
                headers={
                    "content-type": "application/x-www-form-urlencoded",
                    "accept": "application/json"
                },
                data=token_data,
                timeout=30
            )

            if response.status_code != 200:
                result.error_message = f"OAuth token refresh failed: HTTP {response.status_code}"
                logger.warning(f"{result.error_message}, response: {response.text[:200]}")
                return result

            data = response.json()

            #Extract token
            access_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token", refresh_token)
            expires_in = data.get("expires_in", 3600)

            if not access_token:
                result.error_message = "OAuth token refresh failed: access_token not found"
                logger.warning(result.error_message)
                return result

            # Calculate expiration time
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            result.success = True
            result.access_token = access_token
            result.refresh_token = new_refresh_token
            result.expires_at = expires_at

            logger.info(f"OAuth token refreshed successfully, expiration time: {expires_at}")
            return result

        except Exception as e:
            result.error_message = f"OAuth token refresh exception: {str(e)}"
            logger.error(result.error_message)
            return result

    def refresh_account(self, account: Account) -> TokenRefreshResult:
        """
        Refresh account Token

        Priority:
        1. Session Token refresh
        2. OAuth Refresh Token refresh

        Args:
            account: account object

        Returns:
            TokenRefreshResult: Refresh the result
        """
        # Try Session Token first
        if account.session_token:
            logger.info(f"Try to use Session Token to refresh account {account.email}")
            result = self.refresh_by_session_token(account.session_token)
            if result.success:
                return result
            logger.warning(f"Session Token refresh failed, try OAuth refresh")

        # Try OAuth Refresh Token
        if account.refresh_token:
            logger.info(f"Try to use OAuth Refresh Token to refresh account {account.email}")
            result = self.refresh_by_oauth_token(
                refresh_token=account.refresh_token,
                client_id=account.client_id
            )
            return result

        # No refresh method available
        return TokenRefreshResult(
            success=False,
            error_message="No refresh method available for account (missing session_token and refresh_token)"
        )

    def validate_token(self, access_token: str) -> Tuple[bool, Optional[str]]:
        """
        Verify whether the Access Token is valid

        Args:
            access_token: access token

        Returns:
            Tuple[bool, Optional[str]]: (valid, error message)
        """
        try:
            session = self._create_session()

            # Call OpenAI API to verify token
            response = session.get(
                "https://chatgpt.com/backend-api/me",
                headers={
                    "authorization": f"Bearer {access_token}",
                    "accept": "application/json"
                },
                timeout=30
            )

            if response.status_code == 200:
                return True, None
            elif response.status_code == 401:
                return False, "Token is invalid or expired"
            elif response.status_code == 403:
                return False, "Account may be banned"
            else:
                return False, f"Authentication failed: HTTP {response.status_code}"

        except Exception as e:
            return False, f"Verification exception: {str(e)}"


def refresh_account_token(account_id: int, proxy_url: Optional[str] = None) -> TokenRefreshResult:
    """
    Refresh the token of the specified account and update the database

    Args:
        account_id: account ID
        proxy_url: proxy URL

    Returns:
        TokenRefreshResult: Refresh the result
    """
    with get_db() as db:
        account = crud.get_account_by_id(db, account_id)
        if not account:
            return TokenRefreshResult(success=False, error_message="Account does not exist")

        manager = TokenRefreshManager(proxy_url=proxy_url)
        result = manager.refresh_account(account)

        if result.success:
            # Update database
            update_data = {
                "access_token": result.access_token,
                "last_refresh": datetime.utcnow()
            }

            if result.refresh_token:
                update_data["refresh_token"] = result.refresh_token

            if result.expires_at:
                update_data["expires_at"] = result.expires_at

            crud.update_account(db, account_id, **update_data)

        return result


def validate_account_token(account_id: int, proxy_url: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Verify whether the Token of the specified account is valid

    Args:
        account_id: account ID
        proxy_url: proxy URL

    Returns:
        Tuple[bool, Optional[str]]: (valid, error message)
    """
    with get_db() as db:
        account = crud.get_account_by_id(db, account_id)
        if not account:
            return False, "Account does not exist"

        if not account.access_token:
            return False, "Account does not have access_token"

        manager = TokenRefreshManager(proxy_url=proxy_url)
        return manager.validate_token(account.access_token)
