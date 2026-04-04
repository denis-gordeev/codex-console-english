import importlib

import pytest
from fastapi.testclient import TestClient
from pydantic.types import SecretStr

web_app = importlib.import_module("src.web.app")
settings_module = importlib.import_module("src.config.settings")


def test_create_app_runs_lifespan_startup(monkeypatch):
    initialized = []
    loop_states = []

    monkeypatch.setattr(
        "src.database.init_db.initialize_database",
        lambda: initialized.append(True),
    )
    monkeypatch.setattr(
        web_app.task_manager,
        "set_loop",
        lambda loop: loop_states.append(loop.is_running()),
    )

    app = web_app.create_app()

    with TestClient(app):
        pass

    assert initialized == [True]
    assert loop_states == [True]


def _build_test_client(monkeypatch):
    monkeypatch.setattr(
        "src.database.init_db.initialize_database",
        lambda: None,
    )
    monkeypatch.setattr(
        web_app.task_manager,
        "set_loop",
        lambda loop: None,
    )
    monkeypatch.setattr(
        web_app,
        "get_settings",
        lambda: settings_module.Settings(
            webui_access_password=SecretStr("letmein"),
            webui_secret_key=SecretStr("test-secret"),
        ),
    )
    return TestClient(web_app.create_app())


def test_protected_routes_redirect_to_login_with_next_query(monkeypatch):
    client = _build_test_client(monkeypatch)

    response = client.get("/accounts?tab=active", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/login?next=%2Faccounts%3Ftab%3Dactive"


def test_login_sets_cookie_and_redirects_back_to_local_page(monkeypatch):
    client = _build_test_client(monkeypatch)

    response = client.post(
        "/login",
        data={"password": "letmein", "next": "/settings?section=proxy"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/settings?section=proxy"
    assert "webui_auth=" in response.headers["set-cookie"]


def test_login_rejects_invalid_password(monkeypatch):
    client = _build_test_client(monkeypatch)

    response = client.post(
        "/login",
        data={"password": "wrong", "next": "/accounts"},
    )

    assert response.status_code == 401
    assert "Incorrect password" in response.text


def test_login_normalizes_external_next_targets(monkeypatch):
    client = _build_test_client(monkeypatch)

    login_page = client.get("/login?next=https://example.com")
    response = client.post(
        "/login",
        data={"password": "letmein", "next": "https://example.com"},
        follow_redirects=False,
    )

    assert 'name="next" value="/"' in login_page.text
    assert response.status_code == 302
    assert response.headers["location"] == "/"


@pytest.mark.parametrize(
    ("path", "expected_text"),
    [
        ("/accounts", "Account Management"),
        ("/email-services", "Email Service Management"),
        ("/settings", "System Settings"),
    ],
)
def test_authenticated_pages_render_translated_content(monkeypatch, path, expected_text):
    client = _build_test_client(monkeypatch)

    login_response = client.post(
        "/login",
        data={"password": "letmein", "next": path},
        follow_redirects=False,
    )

    assert login_response.status_code == 302
    assert login_response.headers["location"] == path

    response = client.get(path)

    assert response.status_code == 200
    assert expected_text in response.text
    assert "OpenAI Registration System" in response.text


def test_payment_page_renders_translated_content_without_auth(monkeypatch):
    client = _build_test_client(monkeypatch)

    response = client.get("/payment")

    assert response.status_code == 200
    assert "Payment upgrade" in response.text
    assert "Billing country" in response.text
