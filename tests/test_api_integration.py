import importlib
import sys


def _load_app_module(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DISABLE_SCHEDULER", "1")
    sys.modules.pop("backend.app", None)
    return importlib.import_module("backend.app")


def test_apps_and_status_endpoints_with_flask_client(tmp_path, monkeypatch):
    app_module = _load_app_module(tmp_path, monkeypatch)
    client = app_module.app.test_client()

    create_response = client.post(
        "/api/apps",
        json={
            "name": "Integration Test App",
            "app_store_id": "123456789",
            "notification_destinations": [],
            "icon_url": "https://example.com/icon.png",
            "enabled": True,
        },
    )
    assert create_response.status_code == 201
    app_id = create_response.get_json()["id"]

    apps_response = client.get("/api/apps")
    assert apps_response.status_code == 200
    apps = apps_response.get_json()
    assert any(app["id"] == app_id for app in apps)

    status_response = client.get("/api/status")
    assert status_response.status_code == 200
    status_payload = status_response.get_json()
    assert status_payload["status"] == "ok"
    assert "scheduled_jobs_count" in status_payload
