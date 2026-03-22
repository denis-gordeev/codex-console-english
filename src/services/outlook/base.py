"""Outlook service basic definition
Contains enumeration types and data classes"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class ProviderType(str, Enum):
    """Outlook provider type"""
    IMAP_OLD = "imap_old"      # Legacy IMAP (outlook.office365.com)
    IMAP_NEW = "imap_new"      # New version of IMAP (outlook.live.com)
    GRAPH_API = "graph_api"    # Microsoft Graph API


class TokenEndpoint(str, Enum):
    """Token endpoint"""
    LIVE = "https://login.live.com/oauth20_token.srf"
    CONSUMERS = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
    COMMON = "https://login.microsoftonline.com/common/oauth2/v2.0/token"


class IMAPServer(str, Enum):
    """IMAP server"""
    OLD = "outlook.office365.com"
    NEW = "outlook.live.com"


class ProviderStatus(str, Enum):
    """provider status"""
    HEALTHY = "healthy"        # healthy
    DEGRADED = "degraded"      # Downgrade
    DISABLED = "disabled"      # Disable


@dataclass
class EmailMessage:
    """Email message data class"""
    id: str                                    # Message ID
    subject: str                               # theme
    sender: str                                # sender
    recipients: List[str] = field(default_factory=list)  # Recipient list
    body: str = ""                             # Text content
    body_preview: str = ""                     # Text preview
    received_at: Optional[datetime] = None     # Receiving time
    received_timestamp: int = 0                # receive timestamp
    is_read: bool = False                      # Has it been read?
    has_attachments: bool = False              # Is there any attachment?
    raw_data: Optional[bytes] = None           # Raw data (for debugging)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
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
    """Token information data class"""
    access_token: str
    expires_at: float              # Expiration timestamp
    token_type: str = "Bearer"
    scope: str = ""
    refresh_token: Optional[str] = None

    def is_expired(self, buffer_seconds: int = 120) -> bool:
        """Check if the Token has expired"""
        import time
        return time.time() >= (self.expires_at - buffer_seconds)

    @classmethod
    def from_response(cls, data: Dict[str, Any], scope: str = "") -> "TokenInfo":
        """Created from API response"""
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
    """Provider health status"""
    provider_type: ProviderType
    status: ProviderStatus = ProviderStatus.HEALTHY
    failure_count: int = 0                       # Number of consecutive failures
    last_success: Optional[datetime] = None      # last success time
    last_failure: Optional[datetime] = None      # last failure time
    last_error: str = ""                         # last error message
    disabled_until: Optional[datetime] = None    # Disable deadline

    def record_success(self):
        """Record success"""
        self.status = ProviderStatus.HEALTHY
        self.failure_count = 0
        self.last_success = datetime.now()
        self.disabled_until = None

    def record_failure(self, error: str):
        """Logging failed"""
        self.failure_count += 1
        self.last_failure = datetime.now()
        self.last_error = error

    def should_disable(self, threshold: int = 3) -> bool:
        """Determine whether it should be disabled"""
        return self.failure_count >= threshold

    def is_disabled(self) -> bool:
        """Check if disabled"""
        if self.disabled_until and datetime.now() < self.disabled_until:
            return True
        return False

    def disable(self, duration_seconds: int = 300):
        """Disable provider"""
        from datetime import timedelta
        self.status = ProviderStatus.DISABLED
        self.disabled_until = datetime.now() + timedelta(seconds=duration_seconds)

    def enable(self):
        """enable provider"""
        self.status = ProviderStatus.HEALTHY
        self.disabled_until = None
        self.failure_count = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "provider_type": self.provider_type.value,
            "status": self.status.value,
            "failure_count": self.failure_count,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "last_error": self.last_error,
            "disabled_until": self.disabled_until.isoformat() if self.disabled_until else None,
        }
