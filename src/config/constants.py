"""
Constant definitions
"""

import random
from datetime import datetime
from enum import Enum
from typing import Dict, List, Tuple


# ============================================================================
# Enumerations
# ============================================================================

class AccountStatus(str, Enum):
    """Account status"""
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
    """Email service type"""
    TEMPMAIL = "tempmail"
    OUTLOOK = "outlook"
    MOE_MAIL = "moe_mail"
    TEMP_MAIL = "temp_mail"
    DUCK_MAIL = "duck_mail"
    FREEMAIL = "freemail"
    IMAP_MAIL = "imap_mail"


# ============================================================================
# Application constants
# ============================================================================

APP_NAME = "OpenAI/Codex CLI Auto-Registration System"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "System for automatically registering OpenAI/Codex CLI accounts"

# ============================================================================
# OpenAI OAuth constants
# ============================================================================

# OAuth parameters
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
    "EMAIL_OTP_VERIFICATION": "email_otp_verification", # Account already registered; OTP verification required
    "PASSWORD_REGISTRATION": "create_account_password", # New account; password setup required
    "LOGIN_PASSWORD": "login_password", # Login flow; password entry required
}

# ============================================================================
# Email service constants
# ============================================================================

# Tempmail.lol API endpoint
TEMPMAIL_API_ENDPOINTS = {
    "create_inbox": "/inbox/create",
    "get_inbox": "/inbox",
}

# Custom domain email API endpoint
CUSTOM_DOMAIN_API_ENDPOINTS = {
    "get_config": "/api/config",
    "create_email": "/api/emails/generate",
    "list_emails": "/api/emails",
    "get_email_messages": "/api/emails/{emailId}",
    "delete_email": "/api/emails/{emailId}",
    "get_message": "/api/emails/{emailId}/{messageId}",
}

# Default email service configuration
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
# Registration process constants
# ============================================================================

# OTP constants
OTP_CODE_PATTERN = r"(?<!\d)(\d{6})(?!\d)"
OTP_MAX_ATTEMPTS = 40 # Maximum number of polling attempts

# OTP extraction patterns (enhanced)
# Simple match: any 6-digit number
OTP_CODE_SIMPLE_PATTERN = r"(?<!\d)(\d{6})(?!\d)"
# Semantic matching: verification code with context (e.g., "code is 123456", "verification code 123456")
OTP_CODE_SEMANTIC_PATTERN = r'(?:code\s+is|verification code[is]?\s*[::]?\s*)(\d{6})'

# OpenAI verify email sender
OPENAI_EMAIL_SENDERS = [
    "noreply@openai.com",
    "no-reply@openai.com",
    "@openai.com", # Exact domain match
    ".openai.com", # Subdomain match (e.g., otp@tm1.openai.com)
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
        Dictionary containing name and birthdate
    """
    # Randomly select a name
    name = random.choice(FIRST_NAMES)

    # Generate a random birthday (18-45 years old)
    current_year = datetime.now().year
    birth_year = random.randint(current_year - 45, current_year - 18)
    birth_month = random.randint(1, 12)
    # Determine the number of days in the month
    if birth_month in [1, 3, 5, 7, 8, 10, 12]:
        birth_day = random.randint(1, 31)
    elif birth_month in [4, 6, 9, 11]:
        birth_day = random.randint(1, 30)
    else:
        # February; simplified handling
        birth_day = random.randint(1, 28)

    birthdate = f"{birth_year}-{birth_month:02d}-{birth_day:02d}"

    return {
        "name": name,
        "birthdate": birthdate
    }

# Keep default values for compatibility
DEFAULT_USER_INFO = {
    "name": "Neo",
    "birthdate": "2000-02-20",
}

# ============================================================================
# Proxy constants
# ============================================================================

PROXY_TYPES = ["http", "socks5", "socks5h"]
DEFAULT_PROXY_CONFIG = {
    "enabled": False,
    "type": "http",
    "host": "127.0.0.1",
    "port": 7890,
}

# ============================================================================
# Database constants
# ============================================================================

# Database table names
DB_TABLE_NAMES = {
    "accounts": "accounts",
    "email_services": "email_services",
    "registration_tasks": "registration_tasks",
    "settings": "settings",
}

# Default settings
DEFAULT_SETTINGS = [
    # (key, value, description, category)
    ("system.name", APP_NAME, "System name", "general"),
    ("system.version", APP_VERSION, "System version", "general"),
    ("logs.retention_days", "30", "Log retention days", "general"),
    ("openai.client_id", OAUTH_CLIENT_ID, "OpenAI OAuth Client ID", "openai"),
    ("openai.auth_url", OAUTH_AUTH_URL, "OpenAI OAuth authorization URL", "openai"),
    ("openai.token_url", OAUTH_TOKEN_URL, "OpenAI OAuth token URL", "openai"),
    ("openai.redirect_uri", OAUTH_REDIRECT_URI, "OpenAI OAuth callback URI", "openai"),
    ("openai.scope", OAUTH_SCOPE, "OpenAI OAuth scope", "openai"),
    ("proxy.enabled", "false", "Enable proxy", "proxy"),
    ("proxy.type", "http", "Proxy type (http/socks5)", "proxy"),
    ("proxy.host", "127.0.0.1", "Proxy host", "proxy"),
    ("proxy.port", "7890", "Proxy port", "proxy"),
    ("registration.max_retries", "3", "Maximum number of retries", "registration"),
    ("registration.timeout", "120", "timeout (seconds)", "registration"),
    ("registration.default_password_length", "12", "Default password length", "registration"),
    ("webui.host", "0.0.0.0", "Web UI listening host", "webui"),
    ("webui.port", "8000", "Web UI listening port", "webui"),
    ("webui.debug", "true", "Debug mode", "webui"),
]

# ============================================================================
# Web UI constants
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

# API response status codes
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
# Error messages
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
    "OTP_NOT_RECEIVED": "OTP not received",
    "OTP_INVALID": "Invalid OTP",

    # OpenAI related errors
    "OPENAI_AUTH_FAILED": "OpenAI authentication failed",
    "OPENAI_RATE_LIMIT": "OpenAI API rate limit",
    "OPENAI_CAPTCHA": "CAPTCHA encountered",

    # Proxy errors
    "PROXY_FAILED": "Proxy connection failed",
    "PROXY_AUTH_FAILED": "Proxy authentication failed",

    # Account errors
    "ACCOUNT_NOT_FOUND": "Account not found",
    "ACCOUNT_ALREADY_EXISTS": "Account already exists",
    "ACCOUNT_INVALID": "Invalid account",

    # Task errors
    "TASK_NOT_FOUND": "Task not found",
    "TASK_ALREADY_RUNNING": "Task is already running",
    "TASK_CANCELLED": "Task canceled",
}

# ============================================================================
# Regular expressions
# ============================================================================

REGEX_PATTERNS = {
    "EMAIL": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "URL": r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+",
    "IP_ADDRESS": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "OTP_CODE": OTP_CODE_PATTERN,
}

# ============================================================================
# Time constants
# ============================================================================

TIME_CONSTANTS = {
    "SECOND": 1,
    "MINUTE": 60,
    "HOUR": 3600,
    "DAY": 86400,
    "WEEK": 604800,
}


# ============================================================================
# Microsoft/Outlook constants
# ============================================================================

# Microsoft OAuth2 token endpoints
MICROSOFT_TOKEN_ENDPOINTS = {
    # Endpoint for legacy IMAP
    "LIVE": "https://login.live.com/oauth20_token.srf",
    # Endpoint for new IMAP (requires specific scope)
    "CONSUMERS": "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
    # Endpoint for Graph API
    "COMMON": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
}

# IMAP server configuration
OUTLOOK_IMAP_SERVERS = {
    "OLD": "outlook.office365.com",  # Legacy IMAP
    "NEW": "outlook.live.com",  # New IMAP endpoint
}

# Microsoft OAuth2 Scopes
MICROSOFT_SCOPES = {
    # Legacy IMAP does not require a specific scope
    "IMAP_OLD": "",
    # Scope required by new IMAP
    "IMAP_NEW": "https://outlook.office.com/IMAP.AccessAsUser.All offline_access",
    # Scope required by Graph API
    "GRAPH_API": "https://graph.microsoft.com/.default",
}

# Outlook provider default priority
OUTLOOK_PROVIDER_PRIORITY = ["imap_new", "imap_old", "graph_api"]
