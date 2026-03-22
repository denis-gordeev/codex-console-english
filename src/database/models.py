"""
SQLAlchemy ORM model definition
"""

from datetime import datetime
from typing import Optional, Dict, Any
import json
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship

Base = declarative_base()


class JSONEncodedDict(TypeDecorator):
    """JSON encoding dictionary type"""
    impl = Text

    def process_bind_param(self, value: Optional[Dict[str, Any]], dialect):
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value: Optional[str], dialect):
        if value is None:
            return None
        return json.loads(value)


class Account(Base):
    """Registered account table"""
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password = Column(String(255)) #Registration password (clear text storage)
    access_token = Column(Text)
    refresh_token = Column(Text)
    id_token = Column(Text)
    session_token = Column(Text) # Session token (priority refresh method)
    client_id = Column(String(255))  # OAuth Client ID
    account_id = Column(String(255))
    workspace_id = Column(String(255))
    email_service = Column(String(50), nullable=False)  # 'tempmail', 'outlook', 'moe_mail'
    email_service_id = Column(String(255)) # ID in the email service
    proxy_used = Column(String(255))
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_refresh = Column(DateTime) #Last refresh time
    expires_at = Column(DateTime) # Token expiration time
    status = Column(String(20), default='active')  # 'active', 'expired', 'banned', 'failed'
    extra_data = Column(JSONEncodedDict) # Extra information storage
    cpa_uploaded = Column(Boolean, default=False) # Whether it has been uploaded to CPA
    cpa_uploaded_at = Column(DateTime) #Upload time
    source = Column(String(20), default='register') # 'register' or 'login', distinguish the account source
    subscription_type = Column(String(20))  # None / 'plus' / 'team'
    subscription_at = Column(DateTime) # Subscription activation time
    cookies = Column(Text) # Complete cookie string, used for payment requests
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'password': self.password,
            'client_id': self.client_id,
            'email_service': self.email_service,
            'account_id': self.account_id,
            'workspace_id': self.workspace_id,
            'registered_at': self.registered_at.isoformat() if self.registered_at else None,
            'last_refresh': self.last_refresh.isoformat() if self.last_refresh else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'status': self.status,
            'proxy_used': self.proxy_used,
            'cpa_uploaded': self.cpa_uploaded,
            'cpa_uploaded_at': self.cpa_uploaded_at.isoformat() if self.cpa_uploaded_at else None,
            'source': self.source,
            'subscription_type': self.subscription_type,
            'subscription_at': self.subscription_at.isoformat() if self.subscription_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class EmailService(Base):
    """Mailbox service configuration table"""
    __tablename__ = 'email_services'

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_type = Column(String(50), nullable=False)  # 'outlook', 'moe_mail'
    name = Column(String(100), nullable=False)
    config = Column(JSONEncodedDict, nullable=False) # Service configuration (encrypted storage)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0) # Use priority
    last_used = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RegistrationTask(Base):
    """Registration task list"""
    __tablename__ = 'registration_tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_uuid = Column(String(36), unique=True, nullable=False, index=True) # Task unique identifier
    status = Column(String(20), default='pending')  # 'pending', 'running', 'completed', 'failed', 'cancelled'
    email_service_id = Column(Integer, ForeignKey('email_services.id'), index=True) # Email service used
    proxy = Column(String(255)) # proxy used
    logs = Column(Text) #Registration process log
    result = Column(JSONEncodedDict) #Registration result
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # relation
    email_service = relationship('EmailService')


class Setting(Base):
    """System Settings Table"""
    __tablename__ = 'settings'

    key = Column(String(100), primary_key=True)
    value = Column(Text)
    description = Column(Text)
    category = Column(String(50), default='general')  # 'general', 'email', 'proxy', 'openai'
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CpaService(Base):
    """CPA Service Configuration Table"""
    __tablename__ = 'cpa_services'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False) # Service name
    api_url = Column(String(500), nullable=False)  # API URL
    api_token = Column(Text, nullable=False)  # API Token
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0) # Priority
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Sub2ApiService(Base):
    """Sub2API service configuration table"""
    __tablename__ = 'sub2api_services'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False) # Service name
    api_url = Column(String(500), nullable=False)  # API URL (host)
    api_key = Column(Text, nullable=False)  # x-api-key
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0) # Priority
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TeamManagerService(Base):
    """Team Manager Service Configuration Table"""
    __tablename__ = 'tm_services'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False) # Service name
    api_url = Column(String(500), nullable=False)  # API URL
    api_key = Column(Text, nullable=False)  # X-API-Key
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0) # Priority
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Proxy(Base):
    """Agent list table"""
    __tablename__ = 'proxies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False) #Agent name
    type = Column(String(20), nullable=False, default='http')  # http, socks5
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(100))
    password = Column(String(255))
    enabled = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False) # Whether it is the default proxy
    priority = Column(Integer, default=0) # Priority (reserved field)
    last_used = Column(DateTime) # Last used time
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, include_password: bool = False) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'enabled': self.enabled,
            'is_default': self.is_default or False,
            'priority': self.priority,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_password:
            result['password'] = self.password
        else:
            result['has_password'] = bool(self.password)
        return result

    @property
    def proxy_url(self) -> str:
        """Get the complete proxy URL"""
        if self.type == "http":
            scheme = "http"
        elif self.type == "socks5":
            scheme = "socks5"
        else:
            scheme = self.type

        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"

        return f"{scheme}://{auth}{self.host}:{self.port}"