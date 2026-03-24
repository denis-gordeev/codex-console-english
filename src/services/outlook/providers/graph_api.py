"""
Graph API provider
Using the Microsoft Graph REST API
"""

import json
import logging
from typing import List, Optional
from datetime import datetime

from curl_cffi import requests as _requests

from ..base import ProviderType, EmailMessage
from ..account import OutlookAccount
from ..token_manager import TokenManager
from .base import OutlookProvider, ProviderConfig


logger = logging.getLogger(__name__)


class GraphAPIProvider(OutlookProvider):
    """
    Graph API provider
    Get mail using Microsoft Graph REST API
    Requires graph.microsoft.com/.default scope
    """

    # Graph API endpoint
    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
    MESSAGES_ENDPOINT = "/me/mailFolders/inbox/messages"

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.GRAPH_API

    def __init__(
        self,
        account: OutlookAccount,
        config: Optional[ProviderConfig] = None,
    ):
        super().__init__(account, config)

        # Token Manager
        self._token_manager: Optional[TokenManager] = None

        # Note: Graph API must use OAuth2
        if not account.has_oauth():
            logger.warning(
                f"[{self.account.email}] Graph API provider requires OAuth2 configuration"
                f"(client_id + refresh_token)"
            )

    def connect(self) -> bool:
        """
        Verify connection (obtain Token)

        Returns:
            Is the connection successful?
        """
        if not self.account.has_oauth():
            error = "Graph API requires OAuth2 configuration"
            self.record_failure(error)
            logger.error(f"[{self.account.email}] {error}")
            return False

        if not self._token_manager:
            self._token_manager = TokenManager(
                self.account,
                ProviderType.GRAPH_API,
                self.config.proxy_url,
                self.config.timeout,
            )

        # Try to get Token
        token = self._token_manager.get_access_token()
        if token:
            self._connected = True
            self.record_success()
            logger.info(f"[{self.account.email}] Graph API connection successful")
            return True

        return False

    def disconnect(self):
        """Disconnect (clear status)"""
        self._connected = False

    def get_recent_emails(
        self,
        count: int = 20,
        only_unseen: bool = True,
    ) -> List[EmailMessage]:
        """
        Get recent emails

        Args:
            count: Get the quantity
            only_unseen: whether to only get unread

        Returns:
            mailing list
        """
        if not self._connected:
            if not self.connect():
                return []

        try:
            # Get Access Token
            token = self._token_manager.get_access_token()
            if not token:
                self.record_failure("Unable to obtain Access Token")
                return []

            # Build API request
            url = f"{self.GRAPH_API_BASE}{self.MESSAGES_ENDPOINT}"

            params = {
                "$top": count,
                "$select": "id,subject,from,toRecipients,receivedDateTime,isRead,hasAttachments,bodyPreview,body",
                "$orderby": "receivedDateTime desc",
            }

            # Get only unread emails
            if only_unseen:
                params["$filter"] = "isRead eq false"

            # Build proxy configuration
            proxies = None
            if self.config.proxy_url:
                proxies = {"http": self.config.proxy_url, "https": self.config.proxy_url}

            #Send request (curl_cffi automatically URL-encodes params)
            resp = _requests.get(
                url,
                params=params,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Prefer": "outlook.body-content-type='text'",
                },
                proxies=proxies,
                timeout=self.config.timeout,
                impersonate="chrome110",
            )

            if resp.status_code == 401:
                # Token has no Graph permission (client_id is not authorized), clears the cache but does not record health failures
                # Avoid the health checker disabling the provider due to insufficient permissions and affecting other accounts
                if self._token_manager:
                    self._token_manager.clear_cache()
                self._connected = False
                logger.warning(f"[{self.account.email}] Graph API returns 401, client_id may not have Graph permission, skip")
                return []

            if resp.status_code != 200:
                error_body = resp.text[:200]
                self.record_failure(f"HTTP {resp.status_code}: {error_body}")
                logger.error(f"[{self.account.email}] Graph API request failed: HTTP {resp.status_code}")
                return []

            data = resp.json()

            # Parse emails
            messages = data.get("value", [])
            emails = []

            for msg in messages:
                try:
                    email_msg = self._parse_graph_message(msg)
                    if email_msg:
                        emails.append(email_msg)
                except Exception as e:
                    logger.warning(f"[{self.account.email}] failed to parse Graph API email: {e}")

            self.record_success()
            return emails

        except Exception as e:
            self.record_failure(str(e))
            logger.error(f"[{self.account.email}] Graph API failed to get email: {e}")
            return []

    def _parse_graph_message(self, msg: dict) -> Optional[EmailMessage]:
        """
        Parse Graph API messages

        Args:
            msg: Graph API message object

        Returns:
            EmailMessage object
        """
        # Parse sender
        from_info = msg.get("from", {})
        sender_info = from_info.get("emailAddress", {})
        sender = sender_info.get("address", "")

        # Parse the recipient
        recipients = []
        for recipient in msg.get("toRecipients", []):
            addr_info = recipient.get("emailAddress", {})
            addr = addr_info.get("address", "")
            if addr:
                recipients.append(addr)

        # Parse date
        received_at = None
        received_timestamp = 0
        try:
            date_str = msg.get("receivedDateTime", "")
            if date_str:
                # ISO 8601 format
                received_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                received_timestamp = int(received_at.timestamp())
        except Exception:
            pass

        # Get the text
        body_info = msg.get("body", {})
        body = body_info.get("content", "")
        body_preview = msg.get("bodyPreview", "")

        return EmailMessage(
            id=msg.get("id", ""),
            subject=msg.get("subject", ""),
            sender=sender,
            recipients=recipients,
            body=body,
            body_preview=body_preview,
            received_at=received_at,
            received_timestamp=received_timestamp,
            is_read=msg.get("isRead", False),
            has_attachments=msg.get("hasAttachments", False),
        )

    def test_connection(self) -> bool:
        """
        Test Graph API connection

        Returns:
            Is the connection normal?
        """
        try:
            # Try to get an email to test the connection
            emails = self.get_recent_emails(count=1, only_unseen=False)
            return True
        except Exception as e:
            logger.warning(f"[{self.account.email}] Graph API connection test failed: {e}")
            return False
