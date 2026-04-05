"""Web UI entry point."""

import uvicorn
import logging
import sys
from pathlib import Path

# Add the project root directory to the Python path.
# In a PyInstaller build, __file__ points into the temporary unpack directory,
# so the executable directory is used as the project data directory.
import os
if getattr(sys, 'frozen', False):
    # After packaging: use the directory where the executable file is located
    project_root = Path(sys.executable).parent
    _src_root = Path(sys._MEIPASS)
else:
    project_root = Path(__file__).parent
    _src_root = project_root
sys.path.insert(0, str(_src_root))

from src.core.utils import setup_logging
from src.database.init_db import initialize_database
from src.config.settings import get_settings


def _load_dotenv():
    """Load a .env file from the executable directory or project root."""
    env_path = project_root / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def setup_application():
    """Prepare directories, settings, and logging for the Web UI."""
    # Load .env values without overriding existing environment variables.
    _load_dotenv()

    # Store runtime data and logs next to the executable or project root.
    data_dir = project_root / "data"
    logs_dir = project_root / "logs"
    data_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    # Expose resolved runtime paths to the settings and database layers.
    os.environ.setdefault("APP_DATA_DIR", str(data_dir))
    os.environ.setdefault("APP_LOGS_DIR", str(logs_dir))

    # Initialize the database before loading persisted settings.
    try:
        initialize_database()
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise

    # Load application settings after the database is ready.
    settings = get_settings()

    # Write logs into the resolved runtime logs directory.
    log_file = str(logs_dir / Path(settings.log_file).name)
    setup_logging(
        log_level=settings.log_level,
        log_file=log_file
    )

    logger = logging.getLogger(__name__)
    logger.info("Database initialization completed successfully")
    logger.info("Using data directory: %s", data_dir)
    logger.info("Using log directory: %s", logs_dir)
    logger.info("Application setup completed")
    return settings


def start_webui():
    """Start the Web UI server."""
    # Prepare application state before importing the FastAPI app.
    settings = setup_application()

    # Delay the import to avoid circular dependencies during setup.
    from src.web.app import app

    # Configure uvicorn.
    uvicorn_config = {
        "app": "src.web.app:app",
        "host": settings.webui_host,
        "port": settings.webui_port,
        "reload": settings.debug,
        "log_level": "info" if settings.debug else "warning",
        "access_log": settings.debug,
        "ws": "websockets",
    }

    logger = logging.getLogger(__name__)
    logger.info("Web UI available at http://%s:%s", settings.webui_host, settings.webui_port)
    logger.info("Debug mode: %s", settings.debug)

    # Start the server.
    uvicorn.run(**uvicorn_config)


def main():
    """Parse CLI options and launch the Web UI."""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="OpenAI/Codex CLI automatic registration system Web UI")
    parser.add_argument("--host", help="Listening host (can also be set through the WEBUI_HOST environment variable)")
    parser.add_argument("--port", type=int, help="Listening port (can also be set through the WEBUI_PORT environment variable)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode (can also be set via the DEBUG=1 environment variable)")
    parser.add_argument("--reload", action="store_true", help="Enable hot reload")
    parser.add_argument("--log-level", help="Log level (can also be set through the LOG_LEVEL environment variable)")
    parser.add_argument("--access-password", help="Web UI access key (can also be set via the WEBUI_ACCESS_PASSWORD environment variable)")
    args = parser.parse_args()

    # Apply CLI and environment overrides before startup.
    from src.config.settings import update_settings

    updates = {}

    # CLI arguments take precedence over environment variables.
    host = args.host or os.environ.get("WEBUI_HOST")
    if host:
        updates["webui_host"] = host
        
    port = args.port or os.environ.get("WEBUI_PORT")
    if port:
        updates["webui_port"] = int(port)
        
    debug = args.debug or os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")
    if debug:
        updates["debug"] = debug
        
    log_level = args.log_level or os.environ.get("LOG_LEVEL")
    if log_level:
        updates["log_level"] = log_level
        
    access_password = args.access_password or os.environ.get("WEBUI_ACCESS_PASSWORD")
    if access_password:
        updates["webui_access_password"] = access_password

    if updates:
        update_settings(**updates)

    # Start the Web UI.
    start_webui()


if __name__ == "__main__":
    main()
