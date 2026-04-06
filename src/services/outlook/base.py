"""Basic Outlook service types and data models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class ProviderType(str, Enum):
    """Supported Outlook provider types."""
    IMAP_OLD = "imap_old"      # Legacy IMAP (outlook.office365.com)
    IMAP_NEW = "imap_new"      # New IMAP endpoint (outlook.live.com)
    GRAPH_API = "graph_api"    # Microsoft Graph API


class TokenEndpoint(str, Enum):
    """Supported OAuth token endpoints."""
    LIVE = "https://login.live.com/oauth20_token.srf"
    CONSUMERS = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
    COMMON = "https://login.microsoftonline.com/common/oauth2/v2.0/token"


class IMAPServer(str, Enum):
    """Supported IMAP server hostnames."""
    OLD = "outlook.office365.com"
    NEW = "outlook.live.com"


class ProviderStatus(str, Enum):
    """Provider health status."""
    HEALTHY = "healthy"        # Healthy
    DEGRADED = "degraded"      # Degraded
    DISABLED = "disabled"      # Disabled


@dataclass
class EmailMessage:
    """Email message data model."""
    id: str                                    # Message ID
    subject: str                               # Subject line
    sender: str                                # Sender address
    recipients: List[str] = field(default_factory=list)  # Recipient list
    body: str = ""                             # Message body
    body_preview: str = ""                     # Preview text
    received_at: Optional[datetime] = None     # Received time
    received_timestamp: int = 0                # Received timestamp
    is_read: bool = False                      # Whether the message is marked as read
    has_attachments: bool = False              # Whether the message has attachments
    raw_data: Optional[bytes] = None           # Raw message data for debugging

    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary."""
        return {
            "id": self.id,
            "subject": self.subject,
            "sender": self.sender,
            "recipients": self.recipients,
            "body": self.body,
            "body_preview": self.body_preview,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "received_timestamp": self.received_timestamp,
            "is_read": self.is_read,
            "has_attachments": self.has_attachments,
        }


@dataclass
class TokenInfo:
    """OAuth token metadata."""
    access_token: str
    expires_at: float              # Expiration timestamp
    token_type: str = "Bearer"
    scope: str = ""
    refresh_token: Optional[str] = None

    def is_expired(self, buffer_seconds: int = 120) -> bool:
        """Check whether the token has expired."""
        import time
        return time.time() >= (self.expires_at - buffer_seconds)

    @classmethod
    def from_response(cls, data: Dict[str, Any], scope: str = "") -> "TokenInfo":
        """Build a token object from an API response."""
        import time
        return cls(
            access_token=data.get("access_token", ""),
            expires_at=time.time() + data.get("expires_in", 3600),
            token_type=data.get("token_type", "Bearer"),
            scope=scope or data.get("scope", ""),
            refresh_token=data.get("refresh_token"),
        )


@dataclass
class ProviderHealth:
    """Runtime health information for a provider."""
    provider_type: ProviderType
    status: ProviderStatus = ProviderStatus.HEALTHY
    failure_count: int = 0                       # Number of consecutive failures
    last_success: Optional[datetime] = None      # Last successful request time
    last_failure: Optional[datetime] = None      # Last failed request time
    last_error: str = ""                         # Last error message
    disabled_until: Optional[datetime] = None    # Time until the provider stays disabled

    def record_success(self):
        """Record a successful request."""
        self.status = ProviderStatus.HEALTHY
        self.failure_count = 0
        self.last_success = datetime.now()
        self.disabled_until = None

    def record_failure(self, error: str):
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure = datetime.now()
        self.last_error = error

    def should_disable(self, threshold: int = 3) -> bool:
        """Return whether the provider should be disabled."""
        return self.failure_count >= threshold

    def is_disabled(self) -> bool:
        """Return whether the provider is currently disabled."""
        if self.disabled_until and datetime.now() < self.disabled_until:
            return True
        return False

    def disable(self, duration_seconds: int = 300):
        """Disable the provider for the given duration."""
        from datetime import timedelta
        self.status = ProviderStatus.DISABLED
        self.disabled_until = datetime.now() + timedelta(seconds=duration_seconds)

    def enable(self):
        """Re-enable the provider."""
        self.status = ProviderStatus.HEALTHY
        self.disabled_until = None
        self.failure_count = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert the provider health state to a dictionary."""
        return {
            "provider_type": self.provider_type.value,
            "status": self.status.value,
            "failure_count": self.failure_count,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "last_error": self.last_error,
            "disabled_until": self.disabled_until.isoformat() if self.disabled_until else None,
        }
