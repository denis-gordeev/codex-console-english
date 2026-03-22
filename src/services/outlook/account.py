"""
Outlook Account Data Class
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class OutlookAccount:
    """Outlook account information"""
    email: str
    password: str = ""
    client_id: str = ""
    refresh_token: str = ""

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "OutlookAccount":
        """Create account from configuration"""
        return cls(
            email=config.get("email", ""),
            password=config.get("password", ""),
            client_id=config.get("client_id", ""),
            refresh_token=config.get("refresh_token", "")
        )

    def has_oauth(self) -> bool:
        """Does OAuth2 support"""
        return bool(self.client_id and self.refresh_token)

    def validate(self) -> bool:
        """Verify whether the account information is valid"""
        return bool(self.email and self.password) or self.has_oauth()

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "email": self.email,
            "has_oauth": self.has_oauth(),
        }
        if include_sensitive:
            result.update({
                "password": self.password,
                "client_id": self.client_id,
                "refresh_token": self.refresh_token[:20] + "..." if self.refresh_token else "",
            })
        return result

    def __str__(self) -> str:
        """ string represents """
        return f"OutlookAccount({self.email})"
