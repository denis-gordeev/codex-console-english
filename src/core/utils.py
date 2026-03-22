"""
General utility functions
"""

import os
import sys
import json
import time
import random
import string
import secrets
import hashlib
import logging
import base64
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path

from ..config.constants import PASSWORD_CHARSET, DEFAULT_PASSWORD_LENGTH
from ..config.settings import get_settings


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
) -> logging.Logger:
    """
    Configure the logging system

    Args:
        log_level: log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: log file path, if not specified, it will only be output to the console
        log_format: log format

    Returns:
        root logger
    """
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing processors
    root_logger.handlers.clear()

    #Create formatter
    formatter = logging.Formatter(log_format)

    #Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)
    root_logger.addHandler(console_handler)

    # File handler (if log file is specified)
    if log_file:
        # Make sure the log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)

    return root_logger


def generate_password(length: int = DEFAULT_PASSWORD_LENGTH) -> str:
    """
    Generate random password

    Args:
        length: password length

    Returns:
        Random password string
    """
    if length < 4:
        length = 4

    # Make sure the password contains at least one uppercase letter, one lowercase letter and one number
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
    ]

    #Add remaining characters
    password.extend(secrets.choice(PASSWORD_CHARSET) for _ in range(length - 3))

    # Randomly shuffle
    secrets.SystemRandom().shuffle(password)

    return ''.join(password)


def generate_random_string(length: int = 8) -> str:
    """
    Generate random string (letters only)

    Args:
        length: string length

    Returns:
        random string
    """
    chars = string.ascii_letters
    return ''.join(secrets.choice(chars) for _ in range(length))


def generate_uuid() -> str:
    """Generate UUID string"""
    return str(uuid.uuid4())


def get_timestamp() -> int:
    """Get the current timestamp (seconds)"""
    return int(time.time())


def format_datetime(dt: Optional[datetime] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format date time

    Args:
        dt: datetime object, if None the current time is used
        fmt: format string

    Returns:
        Formatted string
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def parse_datetime(dt_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """
    Parse datetime string

    Args:
        dt_str: date and time string
        fmt: format string

    Returns:
        Datetime object, returns None if parsing fails
    """
    try:
        return datetime.strptime(dt_str, fmt)
    except (ValueError, TypeError):
        return None


def human_readable_size(size_bytes: int) -> str:
    """
    Convert byte size to human readable format

    Args:
        size_bytes: size in bytes

    Returns:
        human readable string
    """
    if size_bytes < 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0

    while size_bytes >= 1024 and unit_index < len(units) - 1:
        size_bytes /= 1024
        unit_index += 1

    return f"{size_bytes:.2f} {units[unit_index]}"


def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Any:
    """
    Retry decorator/function with exponential backoff

    Args:
        func: function to retry
        max_retries: Maximum number of retries
        base_delay: base delay (seconds)
        max_delay: maximum delay (seconds)
        backoff_factor: backoff factor
        exceptions: the type of exceptions to be caught

    Returns:
        function return value

    Raises:
        Exception on last attempt
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e

            # If it is the last attempt, throw an exception directly
            if attempt == max_retries:
                break

            # Calculate delay time
            delay = min(base_delay * (backoff_factor ** attempt), max_delay)

            # Add random jitter
            delay *= (0.5 + random.random())

            # Record log
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Attempt {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                f"Wait {delay:.2f} seconds and try again..."
            )

            time.sleep(delay)

    # All retries fail and the last exception is thrown
    raise last_exception


class RetryDecorator:
    """Retry the decorator class"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        exceptions: tuple = (Exception,)
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.exceptions = exceptions

    def __call__(self, func: Callable) -> Callable:
        """Decorator call"""
        def wrapper(*args, **kwargs):
            def func_to_retry():
                return func(*args, **kwargs)

            return retry_with_backoff(
                func_to_retry,
                max_retries=self.max_retries,
                base_delay=self.base_delay,
                max_delay=self.max_delay,
                backoff_factor=self.backoff_factor,
                exceptions=self.exceptions
            )

        return wrapper


def validate_email(email: str) -> bool:
    """
    Verify email address format

    Args:
        email: email address

    Returns:
        Is it valid?
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """
    Verify URL format

    Args:
        url: URL

    Returns:
        Is it valid?
    """
    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    return bool(re.match(pattern, url))


def sanitize_filename(filename: str) -> str:
    """
    Clean file names to remove unsafe characters

    Args:
        filename: original file name

    Returns:
        Cleaned file name
    """
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    return filename


def read_json_file(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Read JSON file

    Args:
        filepath: file path

    Returns:
        JSON data, returns None if reading fails
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
        logging.getLogger(__name__).warning(f"Failed to read JSON file: {filepath} - {e}")
        return None


def write_json_file(filepath: str, data: Dict[str, Any], indent: int = 2) -> bool:
    """
    Write to JSON file

    Args:
        filepath: file path
        data: data to be written
        indent: number of indent spaces

    Returns:
        Is it successful?
    """
    try:
        # Make sure the directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)

        return True
    except (IOError, TypeError) as e:
        logging.getLogger(__name__).error(f"Failed to write JSON file: {filepath} - {e}")
        return False


def get_project_root() -> Path:
    """
    Get the project root directory

    Returns:
        Project root directory Path object
    """
    # Directory where the current file is located
    current_dir = Path(__file__).parent

    # Search upward until you find the project root directory (containing pyproject.toml or setup.py)
    for parent in [current_dir] + list(current_dir.parents):
        if (parent / "pyproject.toml").exists() or (parent / "setup.py").exists():
            return parent

    # If not found, return the parent directory of the current directory
    return current_dir.parent


def get_data_dir() -> Path:
    """
    Get data directory

    Returns:
        Data directory Path object
    """
    settings = get_settings()
    if not settings.database_url.startswith("sqlite"):
        data_dir = Path(os.environ.get("APP_DATA_DIR", "data"))
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    data_dir = Path(settings.database_url).parent

    # If database_url is a SQLite URL, extract the path
    if settings.database_url.startswith("sqlite:///"):
        db_path = settings.database_url[10:] # Remove "sqlite:///"
        data_dir = Path(db_path).parent

    # Make sure the directory exists
    data_dir.mkdir(parents=True, exist_ok=True)

    return data_dir


def get_logs_dir() -> Path:
    """
    Get log directory

    Returns:
        Log directory Path object
    """
    settings = get_settings()
    log_file = Path(settings.log_file)
    log_dir = log_file.parent

    # Make sure the directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    return log_dir


def format_duration(seconds: int) -> str:
    """
    Format duration

    Args:
        seconds: number of seconds

    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds}seconds"

    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}minutes{seconds}seconds"

    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}hours{minutes}minutes"

    days, hours = divmod(hours, 24)
    return f"{days}days{hours}hours"


def mask_sensitive_data(data: Union[str, Dict, List], mask_char: str = "*") -> Union[str, Dict, List]:
    """
    Mask sensitive data

    Args:
        data: data to be masked
        mask_char: mask character

    Returns:
        masked data
    """
    if isinstance(data, str):
        # If it is a mailbox, mask the middle part
        if "@" in data:
            local, domain = data.split("@", 1)
            if len(local) > 2:
                masked_local = local[0] + mask_char * (len(local) - 2) + local[-1]
            else:
                masked_local = mask_char * len(local)
            return f"{masked_local}@{domain}"

        # If it is a token or key, mask most of the content
        if len(data) > 10:
            return data[:4] + mask_char * (len(data) - 8) + data[-4:]
        return mask_char * len(data)

    elif isinstance(data, dict):
        masked_dict = {}
        for key, value in data.items():
            # Sensitive field name
            sensitive_keys = ["password", "token", "secret", "key", "auth", "credential"]
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                masked_dict[key] = mask_sensitive_data(value, mask_char)
            else:
                masked_dict[key] = value
        return masked_dict

    elif isinstance(data, list):
        return [mask_sensitive_data(item, mask_char) for item in data]

    return data


def calculate_md5(data: Union[str, bytes]) -> str:
    """
    Calculate MD5 hash

    Args:
        data: the data to be hashed

    Returns:
        MD5 hash string
    """
    if isinstance(data, str):
        data = data.encode('utf-8')

    return hashlib.md5(data).hexdigest()


def calculate_sha256(data: Union[str, bytes]) -> str:
    """
    Calculate SHA256 hash

    Args:
        data: the data to be hashed

    Returns:
        SHA256 hash string
    """
    if isinstance(data, str):
        data = data.encode('utf-8')

    return hashlib.sha256(data).hexdigest()


def base64_encode(data: Union[str, bytes]) -> str:
    """Base64 encoding"""
    if isinstance(data, str):
        data = data.encode('utf-8')

    return base64.b64encode(data).decode('utf-8')


def base64_decode(data: str) -> str:
    """Base64 decoding"""
    try:
        decoded = base64.b64decode(data)
        return decoded.decode('utf-8')
    except (base64.binascii.Error, UnicodeDecodeError):
        return ""


class Timer:
    """Timer context manager"""

    def __init__(self, name: str = "operation"):
        self.name = name
        self.start_time = None
        self.elapsed = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.time() - self.start_time
        logger = logging.getLogger(__name__)
        logger.debug(f"{self.name} took: {self.elapsed:.2f} seconds")

    def get_elapsed(self) -> float:
        """Get the elapsed time (seconds)"""
        if self.elapsed is not None:
            return self.elapsed
        if self.start_time is not None:
            return time.time() - self.start_time
        return 0.0
