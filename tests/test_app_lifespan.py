import importlib

from fastapi.testclient import TestClient

web_app = importlib.import_module("src.web.app")


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
