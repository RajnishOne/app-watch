from backend.storage import StorageManager


def test_auth_credentials_are_stripped_on_startup(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    auth_file = data_dir / "auth.json"
    auth_file.write_text(
        """
{
  "enabled": true,
  "auth_type": "forms",
  "username": "admin",
  "password_hash": "abc123hash",
  "bypass_local_networks": true,
  "api_key": "keep-this-api-key"
}
""".strip()
    )

    storage = StorageManager(data_dir)
    auth = storage.get_auth()

    assert auth["enabled"] is False
    assert auth["username"] == ""
    assert auth["password_hash"] == ""
    assert auth["api_key"] == "keep-this-api-key"


def test_settings_defaults_are_merged_with_saved_values(tmp_path):
    storage = StorageManager(tmp_path / "data")
    storage.save_settings(
        {
            "default_interval": "6h",
            "smtp_host": "smtp.example.com",
        }
    )

    settings = storage.get_settings()

    assert settings["default_interval"] == "6h"
    assert settings["smtp_host"] == "smtp.example.com"
    assert settings["smtp_port"] == "587"
    assert settings["message_format_bullet"] == "- "
    assert settings["message_format_normalize_headers"] is True
    assert settings["message_format_name_fixed"] == "Fixed"
    assert settings["message_format_custom_headers"] == ""


def test_apps_crud_round_trip(tmp_path):
    storage = StorageManager(tmp_path / "data")
    app_payload = {
        "name": "Example App",
        "app_store_id": "123456789",
        "notification_destinations": [],
        "enabled": True,
    }

    app_id = storage.save_app(app_payload)
    saved = storage.get_app(app_id)

    assert saved is not None
    assert saved["id"] == app_id
    assert saved["name"] == "Example App"
    assert saved["app_store_id"] == "123456789"
    assert saved["app_store_country"] == "us"

    storage.save_last_version(app_id, "1.2.3")
    storage.save_current_version(app_id, "1.2.4")
    storage.update_last_check(app_id, "2026-01-01T00:00:00")

    assert len(storage.get_all_apps()) == 1

    app_dir = storage.data_dir / "apps" / app_id
    assert (app_dir / "version.txt").exists()
    assert (app_dir / "current_version.txt").exists()
    assert (app_dir / "check.txt").exists()

    assert storage.delete_app(app_id) is True
    assert storage.get_app(app_id) is None
    assert not (app_dir / "version.txt").exists()
    assert not (app_dir / "current_version.txt").exists()
    assert not (app_dir / "check.txt").exists()
