"""FastAPI application entrypoint for the lightweight Web UI."""

import logging
import sys
import secrets
import hmac
import hashlib
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path
from urllib.parse import urlencode

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

# Resolve the resource root for both source and packaged runs.
if getattr(sys, 'frozen', False):
    _RESOURCE_ROOT = Path(sys._MEIPASS)
else:
    _RESOURCE_ROOT = Path(__file__).parent.parent.parent

# Static assets and templates live under the resolved resource root.
STATIC_DIR = _RESOURCE_ROOT / "static"
TEMPLATES_DIR = _RESOURCE_ROOT / "templates"


def _build_static_asset_version(static_dir: Path) -> str:
    """Use the latest static-file mtime as a cache-busting version string."""
    latest_mtime = 0
    if static_dir.exists():
        for path in static_dir.rglob("*"):
            if path.is_file():
                latest_mtime = max(latest_mtime, int(path.stat().st_mtime))
    return str(latest_mtime or 1)


def _normalize_next_path(next_path: Optional[str], default: str = "/") -> str:
    """Allow redirects only to local absolute paths within this app."""
    if not next_path:
        return default
    if not next_path.startswith("/") or next_path.startswith("//"):
        return default
    return next_path


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Initialize shared runtime state during app startup."""
        from ..database.init_db import initialize_database
        import asyncio

        try:
            initialize_database()
        except Exception as e:
            logger.warning(f"Database initialization failed: {e}")

        task_manager.set_loop(asyncio.get_running_loop())

        logger.info("=" * 50)
        logger.info(f"Starting {settings.app_name} v{settings.app_version}")
        logger.info(f"Debug mode: {settings.debug}")
        logger.info(f"Database connection: {settings.database_url}")
        logger.info("=" * 50)

        yield

        logger.info("Application shutdown complete")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="OpenAI/Codex CLI automatic registration system Web UI",
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        logger.info(f"Static asset directory: {STATIC_DIR}")
    else:
        # Create the static directory if it is missing.
        STATIC_DIR.mkdir(parents=True, exist_ok=True)
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        logger.info(f"Created static asset directory: {STATIC_DIR}")

    # Create the template directory if it is missing.
    if not TEMPLATES_DIR.exists():
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created template directory: {TEMPLATES_DIR}")

    # Register API routes
    app.include_router(api_router, prefix="/api")

    # Register WebSocket routes
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
        next_path = request.url.path
        if request.url.query:
            next_path = f"{next_path}?{request.url.query}"
        return RedirectResponse(
            url=f"/login?{urlencode({'next': next_path})}",
            status_code=302,
        )

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, next: Optional[str] = "/"):
        """Render the Web UI login page."""
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "", "next": _normalize_next_path(next)},
        )

    @app.post("/login")
    async def login_submit(
        request: Request,
        password: str = Form(...),
        next: Optional[str] = Form("/"),
    ):
        """Validate the access password and create an auth cookie."""
        expected = get_settings().webui_access_password.get_secret_value()
        if not secrets.compare_digest(password, expected):
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={"error": "Incorrect password", "next": _normalize_next_path(next)},
                status_code=401,
            )

        response = RedirectResponse(url=_normalize_next_path(next), status_code=302)
        response.set_cookie("webui_auth", _auth_token(expected), httponly=True, samesite="lax")
        return response

    @app.get("/logout")
    async def logout(request: Request, next: Optional[str] = "/login"):
        """Clear the auth cookie and return to the login page."""
        response = RedirectResponse(url=_normalize_next_path(next, "/login"), status_code=302)
        response.delete_cookie("webui_auth")
        return response

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Render the registration dashboard."""
        if not _is_authenticated(request):
            return _redirect_to_login(request)
        return templates.TemplateResponse(request=request, name="index.html")

    @app.get("/accounts", response_class=HTMLResponse)
    async def accounts_page(request: Request):
        """Render the account management page."""
        if not _is_authenticated(request):
            return _redirect_to_login(request)
        return templates.TemplateResponse(request=request, name="accounts.html")

    @app.get("/email-services", response_class=HTMLResponse)
    async def email_services_page(request: Request):
        """Render the email service management page."""
        if not _is_authenticated(request):
            return _redirect_to_login(request)
        return templates.TemplateResponse(request=request, name="email_services.html")

    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page(request: Request):
        """Render the settings page."""
        if not _is_authenticated(request):
            return _redirect_to_login(request)
        return templates.TemplateResponse(request=request, name="settings.html")

    @app.get("/payment", response_class=HTMLResponse)
    async def payment_page(request: Request):
        """Render the payment page."""
        return templates.TemplateResponse(request=request, name="payment.html")

    return app


# Global application instance
app = create_app()
