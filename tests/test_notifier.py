import json
import pytest
from unittest.mock import MagicMock, patch
from backend.notifier import NotificationHandler
from backend.app import validate_notification_destination


def test_validate_notification_destination_discord():
    # Valid Discord webhook
    valid, err = validate_notification_destination({
        "type": "discord",
        "webhook_url": "https://discord.com/api/webhooks/123456/token"
    })
    assert valid is True
    assert err is None

    # Missing webhook URL
    valid, err = validate_notification_destination({"type": "discord"})
    assert valid is False
    assert "webhook_url" in err

    # Invalid Discord domain
    valid, err = validate_notification_destination({
        "type": "discord",
        "webhook_url": "https://example.com/api/webhooks/123456/token"
    })
    assert valid is False
    assert "Invalid Discord webhook URL" in err


def test_validate_notification_destination_slack():
    # Valid Slack webhook
    valid, err = validate_notification_destination({
        "type": "slack",
        "webhook_url": "https://hooks.slack.com/services/T00/B00/X00"
    })
    assert valid is True
    assert err is None

    # Invalid Slack webhook URL
    valid, err = validate_notification_destination({
        "type": "slack",
        "webhook_url": "https://slack.com/invalid"
    })
    assert valid is False
    assert "Invalid Slack webhook URL" in err


def test_validate_notification_destination_telegram():
    # Valid with bot_token in dest
    valid, err = validate_notification_destination({
        "type": "telegram",
        "chat_id": "12345678",
        "bot_token": "123:ABC"
    })
    assert valid is True
    assert err is None

    # Valid with bot_token in settings
    valid, err = validate_notification_destination(
        {"type": "telegram", "chat_id": "12345678"},
        settings={"telegram_bot_token": "123:ABC"}
    )
    assert valid is True
    assert err is None

    # Missing bot token
    valid, err = validate_notification_destination({
        "type": "telegram",
        "chat_id": "12345678"
    })
    assert valid is False
    assert "bot_token" in err

    # Missing chat ID
    valid, err = validate_notification_destination({
        "type": "telegram",
        "bot_token": "123:ABC"
    })
    assert valid is False
    assert "chat_id" in err


def test_validate_notification_destination_teams():
    # Valid Teams webhook
    valid, err = validate_notification_destination({
        "type": "teams",
        "webhook_url": "https://outlook.office.com/webhook/abc"
    })
    assert valid is True
    assert err is None

    # Non-HTTPS Teams webhook
    valid, err = validate_notification_destination({
        "type": "teams",
        "webhook_url": "http://outlook.office.com/webhook/abc"
    })
    assert valid is False
    assert "must be HTTPS" in err


def test_validate_notification_destination_email():
    # Valid Email with SMTP host in dest
    valid, err = validate_notification_destination({
        "type": "email",
        "email": "user@example.com",
        "smtp_host": "smtp.example.com"
    })
    assert valid is True
    assert err is None

    # Valid Email with SMTP host in settings
    valid, err = validate_notification_destination(
        {"type": "email", "email": "user@example.com"},
        settings={"smtp_host": "smtp.gmail.com"}
    )
    assert valid is True
    assert err is None

    # Invalid email format
    valid, err = validate_notification_destination({
        "type": "email",
        "email": "invalid-email"
    })
    assert valid is False
    assert "Invalid email address format" in err

    # Missing SMTP host
    valid, err = validate_notification_destination({
        "type": "email",
        "email": "user@example.com"
    })
    assert valid is False
    assert "SMTP host" in err


def test_validate_notification_destination_generic():
    # Valid HTTP/HTTPS
    valid, err = validate_notification_destination({
        "type": "generic",
        "webhook_url": "https://example.com/webhook"
    })
    assert valid is True
    assert err is None

    # Valid template JSON
    valid, err = validate_notification_destination({
        "type": "generic",
        "webhook_url": "https://example.com/webhook",
        "payload_template": '{"app": "{{app_name}}"}'
    })
    assert valid is True
    assert err is None

    # Invalid template JSON
    valid, err = validate_notification_destination({
        "type": "generic",
        "webhook_url": "https://example.com/webhook",
        "payload_template": '{"app": invalid_json}'
    })
    assert valid is False
    assert "Invalid JSON in payload_template" in err


def test_validate_notification_destination_unknown_and_invalid_types():
    # Destination not a dict
    valid, err = validate_notification_destination("string")
    assert valid is False

    # Missing type
    valid, err = validate_notification_destination({})
    assert valid is False

    # Unknown type
    valid, err = validate_notification_destination({"type": "carrier_pigeon"})
    assert valid is False
    assert "Unknown notification type" in err


def test_notification_handler_send_discord():
    handler = NotificationHandler()
    dest = {
        "type": "discord",
        "webhook_url": "https://discord.com/api/webhooks/123/token"
    }

    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        success, err = handler.send_notification(
            dest, "Test App", "1.0.0", "Notes", "Formatted release content"
        )
        assert success is True
        assert err is None
        mock_post.assert_called_once()


def test_notification_handler_send_generic_template():
    handler = NotificationHandler()
    dest = {
        "type": "generic",
        "webhook_url": "https://example.com/webhook",
        "payload_template": '{"name": "{{app_name}}", "ver": "{{version}}"}'
    }

    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        success, err = handler.send_notification(
            dest, "My Cool App", "2.1.0", "Release notes", "Content"
        )
        assert success is True
        assert err is None
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["name"] == "My Cool App"
        assert call_kwargs["json"]["ver"] == "2.1.0"
