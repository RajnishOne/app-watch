import sys
import importlib
from unittest.mock import MagicMock


def _load_app_module(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DISABLE_SCHEDULER", "1")
    sys.modules.pop("backend.app", None)
    return importlib.import_module("backend.app")


def test_get_app_metadata_ios_success(tmp_path, monkeypatch):
    app_module = _load_app_module(tmp_path, monkeypatch)
    client = app_module.app.test_client()

    mock_app_info = {
        "trackName": "Sample iOS App",
        "artistName": "Sample Developer",
        "artworkUrl": "https://example.com/ios-icon.png",
        "version": "1.2.3",
        "bundleId": "com.sample.ios",
    }
    monkeypatch.setattr(app_module.monitor, "fetch_app_info", lambda app_id, country="us": mock_app_info)

    response = client.get("/api/apps/metadata/123456789?platform=ios&country=us")
    assert response.status_code == 200
    data = response.get_json()
    assert data["trackName"] == "Sample iOS App"
    assert data["artistName"] == "Sample Developer"
    assert data["artworkUrl"] == "https://example.com/ios-icon.png"
    assert data["version"] == "1.2.3"
    assert data["bundleId"] == "com.sample.ios"


def test_get_app_metadata_android_success(tmp_path, monkeypatch):
    app_module = _load_app_module(tmp_path, monkeypatch)
    client = app_module.app.test_client()

    mock_android_info = {
        "trackName": "Sample Android App",
        "artistName": "Android Developer",
        "artworkUrl": "https://example.com/android-icon.png",
        "version": "2.0.0",
        "bundleId": "com.sample.android",
    }
    monkeypatch.setattr(app_module.monitor, "fetch_android_app_info", lambda pkg_id, country="us": mock_android_info)

    response = client.get("/api/apps/metadata/com.sample.android?platform=android&country=us")
    assert response.status_code == 200
    data = response.get_json()
    assert data["trackName"] == "Sample Android App"
    assert data["artistName"] == "Android Developer"
    assert data["artworkUrl"] == "https://example.com/android-icon.png"
    assert data["bundleId"] == "com.sample.android"


def test_get_app_metadata_not_found(tmp_path, monkeypatch):
    app_module = _load_app_module(tmp_path, monkeypatch)
    client = app_module.app.test_client()

    monkeypatch.setattr(app_module.monitor, "fetch_app_info", lambda app_id, country="us": None)
    monkeypatch.setattr(app_module.monitor, "fetch_android_app_info", lambda pkg_id, country="us": None)

    # iOS 404
    resp_ios = client.get("/api/apps/metadata/999999999?platform=ios")
    assert resp_ios.status_code == 404
    assert "App not found in App Store" in resp_ios.get_json()["error"]

    # Android 404
    resp_android = client.get("/api/apps/metadata/com.nonexistent?platform=android")
    assert resp_android.status_code == 404
    assert "App not found in Google Play" in resp_android.get_json()["error"]


def test_create_app_with_app_url(tmp_path, monkeypatch):
    app_module = _load_app_module(tmp_path, monkeypatch)
    client = app_module.app.test_client()

    response = client.post(
        "/api/apps",
        json={
            "name": "App Created With URL",
            "app_store_id": "com.example.appurl",
            "platform": "android",
            "app_url": "https://play.google.com/store/apps/details?id=com.example.appurl",
            "app_store_country": "us",
            "icon_url": "https://example.com/icon.png",
            "enabled": True,
            "notification_destinations": [],
        },
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["app_store_id"] == "com.example.appurl"
    assert payload["platform"] == "android"
