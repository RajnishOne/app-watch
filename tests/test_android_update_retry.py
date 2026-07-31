from unittest.mock import Mock

import pytest

from backend.app_store import AppStoreMonitor
from backend.formatter import DiscordFormatter
from backend.storage import StorageManager


@pytest.fixture
def android_monitor(tmp_path, monkeypatch):
    storage = StorageManager(tmp_path / "data")
    app = {
        "id": "android-retry",
        "name": "Android App",
        "app_store_id": "com.example.app",
        "platform": "android",
        "notification_destinations": [{"type": "discord", "webhook_url": "https://example.com"}],
    }
    storage.save_app(app)
    storage.save_last_version(app["id"], "1.0")
    storage.save_last_updated_time(app["id"], 1000)
    # Each check represents a separate scheduler cycle outside the duplicate window.
    monkeypatch.setattr(storage, "get_last_check", lambda app_id: None)
    monitor = AppStoreMonitor(storage, DiscordFormatter(), {"auto_post_on_update": True})
    monkeypatch.setattr(monitor, "fetch_android_app_info", Mock(return_value={
        "version": "1.0",
        "releaseNotes": "Updated release notes",
        "updated": 2000,
    }))
    monkeypatch.setattr(monitor.notifier, "send_notification", Mock(return_value=(True, None)))
    yield monitor, storage, app
    monitor.session.close()


@pytest.mark.parametrize("manual", [False, True])
def test_failed_post_preserves_timestamp_and_next_check_retries(android_monitor, manual):
    monitor, storage, app = android_monitor
    sender = monitor.notifier.send_notification
    sender.side_effect = [(False, "Temporary error"), (True, None)]

    failed = monitor.post_to_discord(app) if manual else monitor.check_app(app)

    assert failed["success"] is False
    assert storage.get_last_updated_time(app["id"]) == "1000"
    assert storage.get_last_version(app["id"]) == "1.0"

    retried = monitor.check_app(app)

    assert retried["success"] is True
    assert retried["update_detected"] is True
    assert storage.get_last_updated_time(app["id"]) == "2000"
    assert sender.call_count == 2
    assert monitor.check_app(app)["update_detected"] is False
    assert sender.call_count == 2


def test_disabled_auto_post_keeps_update_pending(android_monitor):
    monitor, storage, app = android_monitor
    monitor.settings["auto_post_on_update"] = False

    detected = monitor.check_app(app)

    assert detected["update_detected"] is True
    assert detected["auto_post_disabled"] is True
    assert storage.get_last_updated_time(app["id"]) == "1000"
    monitor.notifier.send_notification.assert_not_called()

    monitor.settings["auto_post_on_update"] = True
    assert monitor.check_app(app)["update_detected"] is True
    assert storage.get_last_updated_time(app["id"]) == "2000"
    monitor.notifier.send_notification.assert_called_once()


def test_version_change_is_detected_when_timestamp_is_unchanged(android_monitor):
    monitor, storage, app = android_monitor
    monitor.fetch_android_app_info.return_value.update(version="2.0", updated=1000)

    result = monitor.check_app(app)

    assert result["success"] is True
    assert result["update_detected"] is True
    assert storage.get_last_version(app["id"]) == "2.0"
    monitor.notifier.send_notification.assert_called_once()


def test_successful_manual_post_acknowledges_update(android_monitor):
    monitor, storage, app = android_monitor

    assert monitor.post_to_discord(app)["success"] is True
    assert storage.get_last_updated_time(app["id"]) == "2000"
    assert monitor.check_app(app)["update_detected"] is False
    monitor.notifier.send_notification.assert_called_once()
