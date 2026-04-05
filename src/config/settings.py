"""
Configuration management backed by database storage.

Most settings are stored in the database, with startup-time environment
variables still supported for deployment overrides.
"""

import os
from typing import Optional, Dict, Any, Type, List
from enum import Enum
from pydantic import BaseModel, field_validator
from pydantic.types import SecretStr
from dataclasses import dataclass


class SettingCategory(str, Enum):
    """Set categories"""
    GENERAL = "general"
    DATABASE = "database"
    WEBUI = "webui"
    LOG = "log"
    OPENAI = "openai"
    PROXY = "proxy"
    REGISTRATION = "registration"
    EMAIL = "email"
    TEMPMAIL = "tempmail"
    CUSTOM_DOMAIN = "moe_mail"
    SECURITY = "security"
    CPA = "cpa"


@dataclass
class SettingDefinition:
    """Setting definition"""
    db_key: str
    default_value: Any
    category: SettingCategory
    description: str = ""
    is_secret: bool = False


# Definition of all configuration items (including database key name, default value, classification, description)
SETTING_DEFINITIONS: Dict[str, SettingDefinition] = {
    # Application information
    "app_name": SettingDefinition(
        db_key="app.name",
        default_value="OpenAI/Codex CLI automatic registration system",
        category=SettingCategory.GENERAL,
        description="Application name"
    ),
    "app_version": SettingDefinition(
        db_key="app.version",
        default_value="2.0.0",
        category=SettingCategory.GENERAL,
        description="Application version"
    ),
    "debug": SettingDefinition(
        db_key="app.debug",
        default_value=False,
        category=SettingCategory.GENERAL,
        description="Debug mode"
    ),

    # Database configuration
    "database_url": SettingDefinition(
        db_key="database.url",
        default_value="data/database.db",
        category=SettingCategory.DATABASE,
        description="Database path or connection string"
    ),

    # Web UI configuration
    "webui_host": SettingDefinition(
        db_key="webui.host",
        default_value="0.0.0.0",
        category=SettingCategory.WEBUI,
        description="Web UI listening address"
    ),
    "webui_port": SettingDefinition(
        db_key="webui.port",
        default_value=8000,
        category=SettingCategory.WEBUI,
        description="Web UI listening port"
    ),
    "webui_secret_key": SettingDefinition(
        db_key="webui.secret_key",
        default_value="your-secret-key-change-in-production",
        category=SettingCategory.WEBUI,
        description="Web UI Key",
        is_secret=True
    ),
    "webui_access_password": SettingDefinition(
        db_key="webui.access_password",
        default_value="admin123",
        category=SettingCategory.WEBUI,
        description="Web UI access password",
        is_secret=True
    ),

    # Log configuration
    "log_level": SettingDefinition(
        db_key="log.level",
        default_value="INFO",
        category=SettingCategory.LOG,
        description="Log level"
    ),
    "log_file": SettingDefinition(
        db_key="log.file",
        default_value="logs/app.log",
        category=SettingCategory.LOG,
        description="Log file path"
    ),
    "log_retention_days": SettingDefinition(
        db_key="log.retention_days",
        default_value=30,
        category=SettingCategory.LOG,
        description="Number of days to retain logs"
    ),

    # OpenAI configuration
    "openai_client_id": SettingDefinition(
        db_key="openai.client_id",
        default_value="app_EMoamEEZ73f0CkXaXp7hrann",
        category=SettingCategory.OPENAI,
        description="OpenAI OAuth client ID"
    ),
    "openai_auth_url": SettingDefinition(
        db_key="openai.auth_url",
        default_value="https://auth.openai.com/oauth/authorize",
        category=SettingCategory.OPENAI,
        description="OpenAI OAuth authorization URL"
    ),
    "openai_token_url": SettingDefinition(
        db_key="openai.token_url",
        default_value="https://auth.openai.com/oauth/token",
        category=SettingCategory.OPENAI,
        description="OpenAI OAuth Token URL"
    ),
    "openai_redirect_uri": SettingDefinition(
        db_key="openai.redirect_uri",
        default_value="http://localhost:1455/auth/callback",
        category=SettingCategory.OPENAI,
        description="OpenAI OAuth callback URI"
    ),
    "openai_scope": SettingDefinition(
        db_key="openai.scope",
        default_value="openid email profile offline_access",
        category=SettingCategory.OPENAI,
        description="OpenAI OAuth permission scope"
    ),

    #Agent configuration
    "proxy_enabled": SettingDefinition(
        db_key="proxy.enabled",
        default_value=False,
        category=SettingCategory.PROXY,
        description="Whether to enable proxy"
    ),
    "proxy_type": SettingDefinition(
        db_key="proxy.type",
        default_value="http",
        category=SettingCategory.PROXY,
        description="Proxy type (http/socks5)"
    ),
    "proxy_host": SettingDefinition(
        db_key="proxy.host",
        default_value="127.0.0.1",
        category=SettingCategory.PROXY,
        description="Proxy server address"
    ),
    "proxy_port": SettingDefinition(
        db_key="proxy.port",
        default_value=7890,
        category=SettingCategory.PROXY,
        description="Proxy server port"
    ),
    "proxy_username": SettingDefinition(
        db_key="proxy.username",
        default_value="",
        category=SettingCategory.PROXY,
        description="Agent username"
    ),
    "proxy_password": SettingDefinition(
        db_key="proxy.password",
        default_value="",
        category=SettingCategory.PROXY,
        description="Agent password",
        is_secret=True
    ),
    "proxy_dynamic_enabled": SettingDefinition(
        db_key="proxy.dynamic_enabled",
        default_value=False,
        category=SettingCategory.PROXY,
        description="Whether to enable dynamic proxy"
    ),
    "proxy_dynamic_api_url": SettingDefinition(
        db_key="proxy.dynamic_api_url",
        default_value="",
        category=SettingCategory.PROXY,
        description="Dynamic proxy API address, return proxy URL string"
    ),
    "proxy_dynamic_api_key": SettingDefinition(
        db_key="proxy.dynamic_api_key",
        default_value="",
        category=SettingCategory.PROXY,
        description="Dynamic proxy API key (optional)",
        is_secret=True
    ),
    "proxy_dynamic_api_key_header": SettingDefinition(
        db_key="proxy.dynamic_api_key_header",
        default_value="X-API-Key",
        category=SettingCategory.PROXY,
        description="Dynamic Proxy API Key Request Header Name"
    ),
    "proxy_dynamic_result_field": SettingDefinition(
        db_key="proxy.dynamic_result_field",
        default_value="",
        category=SettingCategory.PROXY,
        description="Extract the field path of the proxy URL from the JSON response (leave blank to use the original response text)"
    ),

    #Register configuration
    "registration_max_retries": SettingDefinition(
        db_key="registration.max_retries",
        default_value=3,
        category=SettingCategory.REGISTRATION,
        description="Maximum number of registration retries"
    ),
    "registration_timeout": SettingDefinition(
        db_key="registration.timeout",
        default_value=120,
        category=SettingCategory.REGISTRATION,
        description="Registration timeout (seconds)"
    ),
    "registration_default_password_length": SettingDefinition(
        db_key="registration.default_password_length",
        default_value=12,
        category=SettingCategory.REGISTRATION,
        description="Default password length"
    ),
    "registration_sleep_min": SettingDefinition(
        db_key="registration.sleep_min",
        default_value=5,
        category=SettingCategory.REGISTRATION,
        description="Minimum registration interval (seconds)"
    ),
    "registration_sleep_max": SettingDefinition(
        db_key="registration.sleep_max",
        default_value=30,
        category=SettingCategory.REGISTRATION,
        description="Maximum registration interval (seconds)"
    ),

    # Email service configuration
    "email_service_priority": SettingDefinition(
        db_key="email.service_priority",
        default_value={"tempmail": 0, "outlook": 1, "moe_mail": 2},
        category=SettingCategory.EMAIL,
        description="Mailbox service priority"
    ),

    # Tempmail.lol configuration
    "tempmail_base_url": SettingDefinition(
        db_key="tempmail.base_url",
        default_value="https://api.tempmail.lol/v2",
        category=SettingCategory.TEMPMAIL,
        description="Tempmail API address"
    ),
    "tempmail_timeout": SettingDefinition(
        db_key="tempmail.timeout",
        default_value=30,
        category=SettingCategory.TEMPMAIL,
        description="Tempmail timeout (seconds)"
    ),
    "tempmail_max_retries": SettingDefinition(
        db_key="tempmail.max_retries",
        default_value=3,
        category=SettingCategory.TEMPMAIL,
        description="Tempmail maximum retries"
    ),

    # Custom domain name email configuration
    "custom_domain_base_url": SettingDefinition(
        db_key="custom_domain.base_url",
        default_value="",
        category=SettingCategory.CUSTOM_DOMAIN,
        description="Custom domain name API address"
    ),
    "custom_domain_api_key": SettingDefinition(
        db_key="custom_domain.api_key",
        default_value="",
        category=SettingCategory.CUSTOM_DOMAIN,
        description="Custom domain name API key",
        is_secret=True
    ),

    # Security configuration
    "encryption_key": SettingDefinition(
        db_key="security.encryption_key",
        default_value="your-encryption-key-change-in-production",
        category=SettingCategory.SECURITY,
        description="Encryption key",
        is_secret=True
    ),

    # Team Manager configuration
    "tm_enabled": SettingDefinition(
        db_key="tm.enabled",
        default_value=False,
        category=SettingCategory.GENERAL,
        description="Whether to enable Team Manager upload"
    ),
    "tm_api_url": SettingDefinition(
        db_key="tm.api_url",
        default_value="",
        category=SettingCategory.GENERAL,
        description="Team Manager API address"
    ),
    "tm_api_key": SettingDefinition(
        db_key="tm.api_key",
        default_value="",
        category=SettingCategory.GENERAL,
        description="Team Manager API Key",
        is_secret=True
    ),

    # CPA upload configuration
    "cpa_enabled": SettingDefinition(
        db_key="cpa.enabled",
        default_value=False,
        category=SettingCategory.CPA,
        description="Whether to enable CPA upload"
    ),
    "cpa_api_url": SettingDefinition(
        db_key="cpa.api_url",
        default_value="",
        category=SettingCategory.CPA,
        description="CPA API address"
    ),
    "cpa_api_token": SettingDefinition(
        db_key="cpa.api_token",
        default_value="",
        category=SettingCategory.CPA,
        description="CPA API Token",
        is_secret=True
    ),

    # Verification code configuration
    "email_code_timeout": SettingDefinition(
        db_key="email_code.timeout",
        default_value=120,
        category=SettingCategory.EMAIL,
        description="Verification code waiting timeout (seconds)"
    ),
    "email_code_poll_interval": SettingDefinition(
        db_key="email_code.poll_interval",
        default_value=3,
        category=SettingCategory.EMAIL,
        description="Verification code polling interval (seconds)"
    ),

    # Outlook configuration
    "outlook_provider_priority": SettingDefinition(
        db_key="outlook.provider_priority",
        default_value=["imap_old", "imap_new", "graph_api"],
        category=SettingCategory.EMAIL,
        description="Outlook provider priority"
    ),
    "outlook_health_failure_threshold": SettingDefinition(
        db_key="outlook.health_failure_threshold",
        default_value=5,
        category=SettingCategory.EMAIL,
        description="Outlook provider consecutive failure threshold"
    ),
    "outlook_health_disable_duration": SettingDefinition(
        db_key="outlook.health_disable_duration",
        default_value=60,
        category=SettingCategory.EMAIL,
        description="Outlook provider disabled for how long (seconds)"
    ),
    "outlook_default_client_id": SettingDefinition(
        db_key="outlook.default_client_id",
        default_value="24d9a0ed-8787-4584-883c-2fd79308940a",
        category=SettingCategory.EMAIL,
        description="Outlook OAuth Default Client ID"
    ),
}

# Mapping of attribute names to database key names (for backward compatibility)
DB_SETTING_KEYS = {name: defn.db_key for name, defn in SETTING_DEFINITIONS.items()}

# Type definition mapping
SETTING_TYPES: Dict[str, Type] = {
    "debug": bool,
    "webui_port": int,
    "log_retention_days": int,
    "proxy_enabled": bool,
    "proxy_port": int,
    "proxy_dynamic_enabled": bool,
    "registration_max_retries": int,
    "registration_timeout": int,
    "registration_default_password_length": int,
    "registration_sleep_min": int,
    "registration_sleep_max": int,
    "email_service_priority": dict,
    "tempmail_timeout": int,
    "tempmail_max_retries": int,
    "tm_enabled": bool,
    "cpa_enabled": bool,
    "email_code_timeout": int,
    "email_code_poll_interval": int,
    "outlook_provider_priority": list,
    "outlook_health_failure_threshold": int,
    "outlook_health_disable_duration": int,
}

# Fields that need to be processed as SecretStr
SECRET_FIELDS = {name for name, defn in SETTING_DEFINITIONS.items() if defn.is_secret}


def _convert_value(attr_name: str, value: str) -> Any:
    """Convert the database string value to the correct type"""
    if attr_name in SECRET_FIELDS:
        return SecretStr(value) if value else SecretStr("")

    target_type = SETTING_TYPES.get(attr_name, str)

    if target_type == bool:
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes", "on")
    elif target_type == int:
        if isinstance(value, int):
            return value
        return int(value) if value else 0
    elif target_type == dict:
        if isinstance(value, dict):
            return value
        if not value:
            return {}
        import json
        import ast
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            try:
                return ast.literal_eval(value)
            except Exception:
                return {}
    elif target_type == list:
        if isinstance(value, list):
            return value
        if not value:
            return []
        import json
        import ast
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            try:
                return ast.literal_eval(value)
            except Exception:
                return []
    else:
        return value


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def _value_to_string(value: Any) -> str:
    """Convert the value to a string stored in the database"""
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (dict, list)):
        import json
        return json.dumps(value)
    elif value is None:
        return ""
    else:
        return str(value)


def init_default_settings() -> None:
    """
    Initialize default settings in database
    If the setting item does not exist, create it and set the default value
    """
    try:
        from ..database.session import get_db
        from ..database.crud import get_setting, set_setting

        with get_db() as db:
            for attr_name, defn in SETTING_DEFINITIONS.items():
                existing = get_setting(db, defn.db_key)
                if not existing:
                    default_value = defn.default_value
                    if attr_name == "database_url":
                        env_url = os.environ.get("APP_DATABASE_URL") or os.environ.get("DATABASE_URL")
                        if env_url:
                            default_value = _normalize_database_url(env_url)
                    default_value = _value_to_string(default_value)
                    set_setting(
                        db,
                        defn.db_key,
                        default_value,
                        category=defn.category.value,
                        description=defn.description
                    )
                    print(f"[Settings] Initialize default settings: {defn.db_key} = {default_value if not defn.is_secret else '***'}")
    except Exception as e:
        if "not initialized" not in str(e):
            print(f"[Settings] Failed to initialize default settings: {e}")


def _load_settings_from_db() -> Dict[str, Any]:
    """Load all settings from database"""
    try:
        from ..database.session import get_db
        from ..database.crud import get_setting

        settings_dict = {}
        with get_db() as db:
            for attr_name, defn in SETTING_DEFINITIONS.items():
                db_setting = get_setting(db, defn.db_key)
                if db_setting:
                    settings_dict[attr_name] = _convert_value(attr_name, db_setting.value)
                else:
                    # There is no such setting in the database, use the default value
                    settings_dict[attr_name] = _convert_value(attr_name, _value_to_string(defn.default_value))
            env_url = os.environ.get("APP_DATABASE_URL") or os.environ.get("DATABASE_URL")
            if env_url:
                settings_dict["database_url"] = _normalize_database_url(env_url)
            env_host = os.environ.get("APP_HOST")
            if env_host:
                settings_dict["webui_host"] = env_host
            env_port = os.environ.get("APP_PORT")
            if env_port:
                try:
                    settings_dict["webui_port"] = int(env_port)
                except ValueError:
                    pass
            env_password = os.environ.get("APP_ACCESS_PASSWORD")
            if env_password:
                settings_dict["webui_access_password"] = env_password
        return settings_dict
    except Exception as e:
        if "not initialized" not in str(e):
            print(f"[Settings] Failed to load settings from database: {e}, use default value")
        return {name: defn.default_value for name, defn in SETTING_DEFINITIONS.items()}


def _save_settings_to_db(**kwargs) -> None:
    """Save settings to database"""
    try:
        from ..database.session import get_db
        from ..database.crud import set_setting

        with get_db() as db:
            for attr_name, value in kwargs.items():
                if attr_name in SETTING_DEFINITIONS:
                    defn = SETTING_DEFINITIONS[attr_name]
                    str_value = _value_to_string(value)
                    set_setting(
                        db,
                        defn.db_key,
                        str_value,
                        category=defn.category.value,
                        description=defn.description
                    )
    except Exception as e:
        if "not initialized" not in str(e):
            print(f"[Settings] Failed to save settings to database: {e}")


class Settings(BaseModel):
    """
    Application configuration - completely based on database storage
    """

    # Application information
    app_name: str = "OpenAI/Codex CLI automatic registration system"
    app_version: str = "2.0.0"
    debug: bool = False

    # Database configuration
    database_url: str = "data/database.db"

    @field_validator('database_url', mode='before')
    @classmethod
    def validate_database_url(cls, v):
        if isinstance(v, str):
            if v.startswith(("postgres://", "postgresql://")):
                return _normalize_database_url(v)
            if v.startswith(("postgresql+psycopg://", "postgresql+psycopg2://")):
                return v
        if isinstance(v, str) and v.startswith("sqlite:///"):
            return v
        if isinstance(v, str) and not v.startswith(("sqlite:///", "postgresql://", "postgresql+psycopg://", "postgresql+psycopg2://", "mysql://")):
            # If it is a file path, convert it to a SQLite URL
            if os.path.isabs(v) or ":/" not in v:
                return f"sqlite:///{v}"
        return v

    # Web UI configuration
    webui_host: str = "0.0.0.0"
    webui_port: int = 8000
    webui_secret_key: SecretStr = SecretStr("your-secret-key-change-in-production")
    webui_access_password: SecretStr = SecretStr("admin123")

    # Log configuration
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    log_retention_days: int = 30

    # OpenAI configuration
    openai_client_id: str = "app_EMoamEEZ73f0CkXaXp7hrann"
    openai_auth_url: str = "https://auth.openai.com/oauth/authorize"
    openai_token_url: str = "https://auth.openai.com/oauth/token"
    openai_redirect_uri: str = "http://localhost:1455/auth/callback"
    openai_scope: str = "openid email profile offline_access"

    #Agent configuration
    proxy_enabled: bool = False
    proxy_type: str = "http"
    proxy_host: str = "127.0.0.1"
    proxy_port: int = 7890
    proxy_username: Optional[str] = None
    proxy_password: Optional[SecretStr] = None
    proxy_dynamic_enabled: bool = False
    proxy_dynamic_api_url: str = ""
    proxy_dynamic_api_key: Optional[SecretStr] = None
    proxy_dynamic_api_key_header: str = "X-API-Key"
    proxy_dynamic_result_field: str = ""

    @property
    def proxy_url(self) -> Optional[str]:
        """Get the complete proxy URL"""
        if not self.proxy_enabled:
            return None

        if self.proxy_type == "http":
            scheme = "http"
        elif self.proxy_type == "socks5":
            scheme = "socks5"
        else:
            return None

        auth = ""
        if self.proxy_username and self.proxy_password:
            auth = f"{self.proxy_username}:{self.proxy_password.get_secret_value()}@"

        return f"{scheme}://{auth}{self.proxy_host}:{self.proxy_port}"

    #Register configuration
    registration_max_retries: int = 3
    registration_timeout: int = 120
    registration_default_password_length: int = 12
    registration_sleep_min: int = 5
    registration_sleep_max: int = 30

    # Email service configuration
    email_service_priority: Dict[str, int] = {"tempmail": 0, "outlook": 1, "moe_mail": 2}

    # Tempmail.lol configuration
    tempmail_base_url: str = "https://api.tempmail.lol/v2"
    tempmail_timeout: int = 30
    tempmail_max_retries: int = 3

    # Custom domain name email configuration
    custom_domain_base_url: str = ""
    custom_domain_api_key: Optional[SecretStr] = None

    # Security configuration
    encryption_key: SecretStr = SecretStr("your-encryption-key-change-in-production")

    # Team Manager configuration
    tm_enabled: bool = False
    tm_api_url: str = ""
    tm_api_key: Optional[SecretStr] = None

    # CPA upload configuration
    cpa_enabled: bool = False
    cpa_api_url: str = ""
    cpa_api_token: SecretStr = SecretStr("")

    # Verification code configuration
    email_code_timeout: int = 120
    email_code_poll_interval: int = 3

    # Outlook configuration
    outlook_provider_priority: List[str] = ["imap_old", "imap_new", "graph_api"]
    outlook_health_failure_threshold: int = 5
    outlook_health_disable_duration: int = 60
    outlook_default_client_id: str = "24d9a0ed-8787-4584-883c-2fd79308940a"


# Global configuration example
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global configuration instance (singleton mode)
    Load configuration entirely from database
    """
    global _settings
    if _settings is None:
        # Initialize the default settings first (if not found in the database)
        init_default_settings()
        # Load all settings from database
        settings_dict = _load_settings_from_db()
        _settings = Settings(**settings_dict)
    return _settings


def update_settings(**kwargs) -> Settings:
    """
    Update configuration and save to database
    """
    global _settings
    if _settings is None:
        _settings = get_settings()

    #Create a new configuration instance
    updated_data = _settings.model_dump()
    updated_data.update(kwargs)
    _settings = Settings(**updated_data)

    # Save to database
    _save_settings_to_db(**kwargs)

    return _settings


def get_database_url() -> str:
    """
    Get database URL (handles relative paths)
    """
    settings = get_settings()
    url = settings.database_url

    # If the URL is a relative path, convert it to an absolute path
    if url.startswith("sqlite:///"):
        path = url[10:] # Remove "sqlite:///"
        if not os.path.isabs(path):
            # Convert to a path relative to the project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            abs_path = os.path.join(project_root, path)
            return f"sqlite:///{abs_path}"

    return url


def get_setting_definition(attr_name: str) -> Optional[SettingDefinition]:
    """Get the definition information of the setting item"""
    return SETTING_DEFINITIONS.get(attr_name)


def get_all_setting_definitions() -> Dict[str, SettingDefinition]:
    """Get the definitions of all setting items"""
    return SETTING_DEFINITIONS.copy()
