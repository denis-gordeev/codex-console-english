"""
constant definition
"""

import random
from datetime import datetime
from enum import Enum
from typing import Dict, List, Tuple


# ============================================================================
# enumeration type
# ============================================================================

class AccountStatus(str, Enum):
    """Account Status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    BANNED = "banned"
    FAILED = "failed"


class TaskStatus(str, Enum):
    """Task status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EmailServiceType(str, Enum):
    """Mailbox service type"""
    TEMPMAIL = "tempmail"
    OUTLOOK = "outlook"
    MOE_MAIL = "moe_mail"
    TEMP_MAIL = "temp_mail"
    DUCK_MAIL = "duck_mail"
    FREEMAIL = "freemail"
    IMAP_MAIL = "imap_mail"


# ============================================================================
# Apply constants
# ============================================================================

APP_NAME = "OpenAI/Codex CLI automatic registration system"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "System for automatically registering OpenAI/Codex CLI accounts"

# ============================================================================
# OpenAI OAuth related constants
# ============================================================================

#OAuth parameters
OAUTH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
OAUTH_AUTH_URL = "https://auth.openai.com/oauth/authorize"
OAUTH_TOKEN_URL = "https://auth.openai.com/oauth/token"
OAUTH_REDIRECT_URI = "http://localhost:1455/auth/callback"
OAUTH_SCOPE = "openid email profile offline_access"

# OpenAI API endpoint
OPENAI_API_ENDPOINTS = {
    "sentinel": "https://sentinel.openai.com/backend-api/sentinel/req",
    "signup": "https://auth.openai.com/api/accounts/authorize/continue",
    "register": "https://auth.openai.com/api/accounts/user/register",
    "password_verify": "https://auth.openai.com/api/accounts/password/verify",
    "send_otp": "https://auth.openai.com/api/accounts/email-otp/send",
    "validate_otp": "https://auth.openai.com/api/accounts/email-otp/validate",
    "create_account": "https://auth.openai.com/api/accounts/create_account",
    "select_workspace": "https://auth.openai.com/api/accounts/workspace/select",
}

# OpenAI page type (used to determine account status)
OPENAI_PAGE_TYPES = {
    "EMAIL_OTP_VERIFICATION": "email_otp_verification", # Account has been registered and OTP verification is required
    "PASSWORD_REGISTRATION": "create_account_password", # New account, need to set a password
    "LOGIN_PASSWORD": "login_password", # Login process, you need to enter a password
}

# ============================================================================
# Email service related constants
# ============================================================================

# Tempmail.lol API endpoint
TEMPMAIL_API_ENDPOINTS = {
    "create_inbox": "/inbox/create",
    "get_inbox": "/inbox",
}

# Custom domain name email API endpoint
CUSTOM_DOMAIN_API_ENDPOINTS = {
    "get_config": "/api/config",
    "create_email": "/api/emails/generate",
    "list_emails": "/api/emails",
    "get_email_messages": "/api/emails/{emailId}",
    "delete_email": "/api/emails/{emailId}",
    "get_message": "/api/emails/{emailId}/{messageId}",
}

#Default configuration of email service
EMAIL_SERVICE_DEFAULTS = {
    "tempmail": {
        "base_url": "https://api.tempmail.lol/v2",
        "timeout": 30,
        "max_retries": 3,
    },
    "outlook": {
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "smtp_server": "smtp.office365.com",
        "smtp_port": 587,
        "timeout": 30,
    },
    "moe_mail": {
        "base_url": "", # Requires user configuration
        "api_key_header": "X-API-Key",
        "timeout": 30,
        "max_retries": 3,
    },
    "duck_mail": {
        "base_url": "",
        "default_domain": "",
        "password_length": 12,
        "timeout": 30,
        "max_retries": 3,
    },
    "freemail": {
        "base_url": "",
        "admin_token": "",
        "domain": "",
        "timeout": 30,
        "max_retries": 3,
    },
    "imap_mail": {
        "host": "",
        "port": 993,
        "use_ssl": True,
        "email": "",
        "password": "",
        "timeout": 30,
        "max_retries": 3,
    }
}

# ============================================================================
#Registration process related constants
# ============================================================================

# Verification code related
OTP_CODE_PATTERN = r"(?<!\d)(\d{6})(?!\d)"
OTP_MAX_ATTEMPTS = 40 # Maximum number of polls

# Verification code extraction regularity (enhanced version)
# Simple match: any 6-digit number
OTP_CODE_SIMPLE_PATTERN = r"(?<!\d)(\d{6})(?!\d)"
# Semantic matching: verification code with context (such as "code is 123456", "Verification code 123456")
OTP_CODE_SEMANTIC_PATTERN = r'(?:code\s+is|Verification code[is]?\s*[::]?\s*)(\d{6})'

# OpenAI verify email sender
OPENAI_EMAIL_SENDERS = [
    "noreply@openai.com",
    "no-reply@openai.com",
    "@openai.com", # Exact domain name matching
    ".openai.com", # Subdomain name matching (such as otp@tm1.openai.com)
]

# OpenAI verification email keywords
OPENAI_VERIFICATION_KEYWORDS = [
    "verify your email",
    "verification code",
    "Verification code",
    "your openai code",
    "code is",
    "one-time code",
]

# Password generation
PASSWORD_CHARSET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
DEFAULT_PASSWORD_LENGTH = 12

# User information generation (for registration)

# Common English names
FIRST_NAMES = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles",
    "Emma", "Olivia", "Ava", "Isabella", "Sophia", "Mia", "Charlotte", "Amelia", "Harper", "Evelyn",
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Avery", "Quinn", "Skyler",
    "Liam", "Noah", "Ethan", "Lucas", "Mason", "Oliver", "Elijah", "Aiden", "Henry", "Sebastian",
    "Grace", "Lily", "Chloe", "Zoey", "Nora", "Aria", "Hazel", "Aurora", "Stella", "Ivy"
]

def generate_random_user_info() -> dict:
    """
    Generate random user information

    Returns:
        dictionary containing name and birthdate
    """
    # Randomly select a name
    name = random.choice(FIRST_NAMES)

    # Generate a random birthday (18-45 years old)
    current_year = datetime.now().year
    birth_year = random.randint(current_year - 45, current_year - 18)
    birth_month = random.randint(1, 12)
    # Determine the number of days based on the month
    if birth_month in [1, 3, 5, 7, 8, 10, 12]:
        birth_day = random.randint(1, 31)
    elif birth_month in [4, 6, 9, 11]:
        birth_day = random.randint(1, 30)
    else:
        # February, simplified processing
        birth_day = random.randint(1, 28)

    birthdate = f"{birth_year}-{birth_month:02d}-{birth_day:02d}"

    return {
        "name": name,
        "birthdate": birthdate
    }

# Keep default values ​​for compatibility
DEFAULT_USER_INFO = {
    "name": "Neo",
    "birthdate": "2000-02-20",
}

# ============================================================================
# Agent related constants
# ============================================================================

PROXY_TYPES = ["http", "socks5", "socks5h"]
DEFAULT_PROXY_CONFIG = {
    "enabled": False,
    "type": "http",
    "host": "127.0.0.1",
    "port": 7890,
}

# ============================================================================
# Database related constants
# ============================================================================

# Database table name
DB_TABLE_NAMES = {
    "accounts": "accounts",
    "email_services": "email_services",
    "registration_tasks": "registration_tasks",
    "settings": "settings",
}

#Default settings
DEFAULT_SETTINGS = [
    # (key, value, description, category)
    ("system.name", APP_NAME, "system name", "general"),
    ("system.version", APP_VERSION, "system version", "general"),
    ("logs.retention_days", "30", "Log retention days", "general"),
    ("openai.client_id", OAUTH_CLIENT_ID, "OpenAI OAuth Client ID", "openai"),
    ("openai.auth_url", OAUTH_AUTH_URL, "OpenAI authentication address", "openai"),
    ("openai.token_url", OAUTH_TOKEN_URL, "OpenAI Token address", "openai"),
    ("openai.redirect_uri", OAUTH_REDIRECT_URI, "OpenAI callback address", "openai"),
    ("openai.scope", OAUTH_SCOPE, "OpenAI permission scope", "openai"),
    ("proxy.enabled", "false", "Whether to enable proxy", "proxy"),
    ("proxy.type", "http", "Proxy type (http/socks5)", "proxy"),
    ("proxy.host", "127.0.0.1", "proxy host", "proxy"),
    ("proxy.port", "7890", "proxy port", "proxy"),
    ("registration.max_retries", "3", "Maximum number of retries", "registration"),
    ("registration.timeout", "120", "timeout (seconds)", "registration"),
    ("registration.default_password_length", "12", "Default password length", "registration"),
    ("webui.host", "0.0.0.0", "Web UI listening host", "webui"),
    ("webui.port", "8000", "Web UI listening port", "webui"),
    ("webui.debug", "true", "debug mode", "webui"),
]

# ============================================================================
# Web UI related constants
# ============================================================================

# WebSocket events
WEBSOCKET_EVENTS = {
    "CONNECT": "connect",
    "DISCONNECT": "disconnect",
    "LOG": "log",
    "STATUS": "status",
    "ERROR": "error",
    "COMPLETE": "complete",
}

# API response status code
API_STATUS_CODES = {
    "SUCCESS": 200,
    "CREATED": 201,
    "BAD_REQUEST": 400,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "INTERNAL_ERROR": 500,
}

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# ============================================================================
# Error message
# ============================================================================

ERROR_MESSAGES = {
    # Common errors
    "DATABASE_ERROR": "Database operation failed",
    "CONFIG_ERROR": "Configuration error",
    "NETWORK_ERROR": "Network connection failed",
    "TIMEOUT": "Operation timeout",
    "VALIDATION_ERROR": "Parameter validation failed",

    # Email service error
    "EMAIL_SERVICE_UNAVAILABLE": "The email service is unavailable",
    "EMAIL_CREATION_FAILED": "Creation of email failed",
    "OTP_NOT_RECEIVED": "Verification code not received",
    "OTP_INVALID": "Verification code is invalid",

    # OpenAI related errors
    "OPENAI_AUTH_FAILED": "OpenAI authentication failed",
    "OPENAI_RATE_LIMIT": "OpenAI interface current limit",
    "OPENAI_CAPTCHA": "Encountered verification code",

    # proxy error
    "PROXY_FAILED": "Proxy connection failed",
    "PROXY_AUTH_FAILED": "Proxy authentication failed",

    #Account error
    "ACCOUNT_NOT_FOUND": "Account does not exist",
    "ACCOUNT_ALREADY_EXISTS": "Account already exists",
    "ACCOUNT_INVALID": "Account is invalid",

    # Task error
    "TASK_NOT_FOUND": "Task does not exist",
    "TASK_ALREADY_RUNNING": "The task is already running",
    "TASK_CANCELLED": "Task has been canceled",
}

# ============================================================================
# Regular expression
# ============================================================================

REGEX_PATTERNS = {
    "EMAIL": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "URL": r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+",
    "IP_ADDRESS": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "OTP_CODE": OTP_CODE_PATTERN,
}

# ============================================================================
# time constant
# ============================================================================

TIME_CONSTANTS = {
    "SECOND": 1,
    "MINUTE": 60,
    "HOUR": 3600,
    "DAY": 86400,
    "WEEK": 604800,
}


# ============================================================================
# Microsoft/Outlook related constants
# ============================================================================

#Microsoft OAuth2 Token endpoint
MICROSOFT_TOKEN_ENDPOINTS = {
    # Endpoint used by older versions of IMAP
    "LIVE": "https://login.live.com/oauth20_token.srf",
    # Endpoint used by the new version of IMAP (requires specific scope)
    "CONSUMERS": "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
    # Endpoint used by Graph API
    "COMMON": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
}

# IMAP server configuration
OUTLOOK_IMAP_SERVERS = {
    "OLD": "outlook.office365.com", # Old version of IMAP
    "NEW": "outlook.live.com", # New version of IMAP
}

# Microsoft OAuth2 Scopes
MICROSOFT_SCOPES = {
    # Older versions of IMAP do not require a specific scope
    "IMAP_OLD": "",
    # Scope required by the new version of IMAP
    "IMAP_NEW": "https://outlook.office.com/IMAP.AccessAsUser.All offline_access",
    #Scope required by Graph API
    "GRAPH_API": "https://graph.microsoft.com/.default",
}

# Outlook provider default priority
OUTLOOK_PROVIDER_PRIORITY = ["imap_new", "imap_old", "graph_api"]
