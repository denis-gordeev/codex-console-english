"""
FastAPI application master file
Lightweight Web UI supports registration, account management, and settings
"""

import logging
import sys
import secrets
import hmac
import hashlib
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from ..config.settings import get_settings
from .routes import api_router
from .routes.websocket import router as ws_router
from .task_manager import task_manager

logger = logging.getLogger(__name__)

# Get the project root directory
# PyInstaller static resources are in sys._MEIPASS after packaging, and in the source code root directory during development
if getattr(sys, 'frozen', False):
    _RESOURCE_ROOT = Path(sys._MEIPASS)
else:
    _RESOURCE_ROOT = Path(__file__).parent.parent.parent

#Static files and template directories
STATIC_DIR = _RESOURCE_ROOT / "static"
TEMPLATES_DIR = _RESOURCE_ROOT / "templates"


def _build_static_asset_version(static_dir: Path) -> str:
    """Generate the version number based on the last modification time of the static file to prevent the browser from continuing to use the old cache after deployment."""
    latest_mtime = 0
    if static_dir.exists():
        for path in static_dir.rglob("*"):
            if path.is_file():
                latest_mtime = max(latest_mtime, int(path.stat().st_mtime))
    return str(latest_mtime or 1)


def create_app() -> FastAPI:
    """Create a FastAPI application instance"""
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Initialize shared runtime state during app startup."""
        from ..database.init_db import initialize_database
        import asyncio

        try:
            initialize_database()
        except Exception as e:
            logger.warning(f"Database initialization: {e}")

        task_manager.set_loop(asyncio.get_running_loop())

        logger.info("=" * 50)
        logger.info(f"{settings.app_name} v{settings.app_version} is starting, the program is stretching...")
        logger.info(f"Debug mode: {settings.debug}")
        logger.info(f"The database connection has been connected: {settings.database_url}")
        logger.info("=" * 50)

        yield

        logger.info("The application is closed, let's close it today")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="OpenAI/Codex CLI automatic registration system Web UI",
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    #CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    #Mount static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        logger.info(f"Static file directory: {STATIC_DIR}")
    else:
        #Create static directory
        STATIC_DIR.mkdir(parents=True, exist_ok=True)
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        logger.info(f"Create static file directory: {STATIC_DIR}")

    #Create template directory
    if not TEMPLATES_DIR.exists():
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Create template directory: {TEMPLATES_DIR}")

    # Register API route
    app.include_router(api_router, prefix="/api")

    # Register WebSocket routing
    app.include_router(ws_router, prefix="/api")

    # Template engine
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.globals["static_version"] = _build_static_asset_version(STATIC_DIR)

    def _auth_token(password: str) -> str:
        secret = get_settings().webui_secret_key.get_secret_value().encode("utf-8")
        return hmac.new(secret, password.encode("utf-8"), hashlib.sha256).hexdigest()

    def _is_authenticated(request: Request) -> bool:
        cookie = request.cookies.get("webui_auth")
        expected = _auth_token(get_settings().webui_access_password.get_secret_value())
        return bool(cookie) and secrets.compare_digest(cookie, expected)

    def _redirect_to_login(request: Request) -> RedirectResponse:
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=302)

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, next: Optional[str] = "/"):
        """Login page"""
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "", "next": next or "/"}
        )

    @app.post("/login")
    async def login_submit(request: Request, password: str = Form(...), next: Optional[str] = "/"):
        """Processing login submission"""
        expected = get_settings().webui_access_password.get_secret_value()
        if not secrets.compare_digest(password, expected):
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Wrong password", "next": next or "/"},
                status_code=401
            )

        response = RedirectResponse(url=next or "/", status_code=302)
        response.set_cookie("webui_auth", _auth_token(expected), httponly=True, samesite="lax")
        return response

    @app.get("/logout")
    async def logout(request: Request, next: Optional[str] = "/login"):
        """Log out"""
        response = RedirectResponse(url=next or "/login", status_code=302)
        response.delete_cookie("webui_auth")
        return response

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Home - Registration Page"""
        if not _is_authenticated(request):
            return _redirect_to_login(request)
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/accounts", response_class=HTMLResponse)
    async def accounts_page(request: Request):
        """Account management page"""
        if not _is_authenticated(request):
            return _redirect_to_login(request)
        return templates.TemplateResponse("accounts.html", {"request": request})

    @app.get("/email-services", response_class=HTMLResponse)
    async def email_services_page(request: Request):
        """Mailbox service management page"""
        if not _is_authenticated(request):
            return _redirect_to_login(request)
        return templates.TemplateResponse("email_services.html", {"request": request})

    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page(request: Request):
        """Settings page"""
        if not _is_authenticated(request):
            return _redirect_to_login(request)
        return templates.TemplateResponse("settings.html", {"request": request})

    @app.get("/payment", response_class=HTMLResponse)
    async def payment_page(request: Request):
        """Payment page"""
        return templates.TemplateResponse("payment.html", {"request": request})

    return app


# Create a global application instance
app = create_app()
