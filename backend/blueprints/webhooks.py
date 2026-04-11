import requests
from flask import Blueprint, jsonify, request


def send_custom_message_to_webhook(destination, message, webhook_type, logger):
    webhook_url = destination.get("webhook_url", "").strip()
    if not webhook_url:
        return False, "Webhook URL is required"

    try:
        if webhook_type == "discord":
            payload = {"content": message}
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True, None
        if webhook_type == "slack":
            payload = {"text": message}
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True, None
        if webhook_type == "teams":
            payload = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": "Custom Message",
                "themeColor": "0078D4",
                "title": "Custom Message",
                "text": message,
            }
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True, None

        payload = {"message": message, "content": message}
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        return True, None
    except requests.exceptions.ConnectionError as e:
        error_str = str(e).lower()
        if "name resolution" in error_str or "failed to resolve" in error_str or "dns" in error_str:
            logger.error(f"DNS resolution error for webhook {webhook_url}: {e}")
            return False, "Network error: Unable to resolve webhook hostname. Please check your internet connection and DNS settings."
        if "connection refused" in error_str or "connection timeout" in error_str:
            logger.error(f"Connection error for webhook {webhook_url}: {e}")
            return False, "Connection error: Unable to connect to webhook server. Please check the webhook URL and your network connection."
        logger.error(f"Connection error for webhook {webhook_url}: {e}")
        return False, "Connection error: Unable to reach webhook server. Please check your network connection."
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout error for webhook {webhook_url}: {e}")
        return False, "Request timeout: The webhook server did not respond in time. Please try again later."
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error for webhook {webhook_url}: {e}")
        status_code = e.response.status_code if hasattr(e, "response") and e.response else None
        if status_code == 404:
            return False, "Webhook not found (404). Please verify the webhook URL is correct."
        if status_code in (401, 403):
            return False, "Webhook authentication failed. Please verify the webhook URL is valid and not expired."
        if status_code == 429:
            return False, "Rate limit exceeded. Please wait a moment before trying again."
        return False, f"HTTP error ({status_code or 'unknown'}): Webhook server returned an error."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error posting to webhook {webhook_url}: {e}")
        error_str = str(e)
        if "HTTPSConnectionPool" in error_str or "HTTPConnectionPool" in error_str:
            if "Caused by" in error_str:
                error_str = error_str.split("Caused by")[-1].strip()
            else:
                parts = error_str.split(":")
                if len(parts) > 1:
                    error_str = parts[-1].strip()
        return False, f"Failed to send message: {error_str}"


def create_webhooks_blueprint(storage, require_auth, load_apps, logger):
    bp = Blueprint("webhooks_api", __name__)
    auth_required = require_auth(storage)

    @bp.route("/api/webhooks/list", methods=["GET"])
    @auth_required
    def list_webhooks():
        try:
            apps = load_apps()
            webhooks = []

            for app in apps:
                app_name = app.get("name", "Unknown")
                notification_destinations = app.get("notification_destinations", [])
                if not notification_destinations and app.get("webhook_url"):
                    notification_destinations = [{"type": "discord", "webhook_url": app["webhook_url"]}]

                for dest in notification_destinations:
                    dest_type = dest.get("type", "").lower()
                    webhook_url = dest.get("webhook_url", "").strip()
                    if dest_type in ["discord", "slack", "teams", "generic"] and webhook_url:
                        webhooks.append(
                            {
                                "id": f"{app['id']}_{len(webhooks)}",
                                "app_name": app_name,
                                "app_id": app["id"],
                                "type": dest_type,
                                "webhook_url": webhook_url,
                                "label": f"{app_name} - {dest_type.capitalize()}",
                            }
                        )
            return jsonify({"webhooks": webhooks})
        except Exception as e:
            logger.error(f"Error listing webhooks: {e}", exc_info=True)
            return jsonify({"error": "Failed to list webhooks"}), 500

    @bp.route("/api/webhooks/send", methods=["POST"])
    @auth_required
    def send_custom_webhook():
        if not request.json:
            return jsonify({"error": "Request body must be JSON"}), 400

        data = request.json
        message = data.get("message", "").strip()
        webhook_urls = data.get("webhook_urls", [])

        if not message:
            return jsonify({"error": "Message is required"}), 400
        if not webhook_urls or not isinstance(webhook_urls, list) or len(webhook_urls) == 0:
            return jsonify({"error": "At least one webhook URL is required"}), 400

        for url in webhook_urls:
            if not isinstance(url, str) or not url.strip():
                return jsonify({"error": "Invalid webhook URL"}), 400
            if not url.startswith("http://") and not url.startswith("https://"):
                return jsonify({"error": "Webhook URL must start with http:// or https://"}), 400

        try:
            success_count = 0
            error_messages = []
            results = []

            for webhook_url in webhook_urls:
                webhook_url = webhook_url.strip()
                webhook_type = "generic"
                if webhook_url.startswith("https://discord.com/api/webhooks/"):
                    webhook_type = "discord"
                elif webhook_url.startswith("https://hooks.slack.com/"):
                    webhook_type = "slack"
                elif "office.com" in webhook_url or "office365" in webhook_url:
                    webhook_type = "teams"

                destination = {"type": webhook_type, "webhook_url": webhook_url}
                success, error_msg = send_custom_message_to_webhook(destination, message, webhook_type, logger)

                if success:
                    success_count += 1
                    results.append({"webhook_url": webhook_url, "status": "success"})
                else:
                    error_messages.append(f"{webhook_url}: {error_msg or 'Failed'}")
                    results.append({"webhook_url": webhook_url, "status": "error", "error": error_msg})

            storage.add_history_entry(
                event_type="webhook_broadcast",
                app_id=None,
                app_name="Custom Message",
                status="success" if success_count > 0 else "error",
                message=f"Custom message sent to {success_count} webhook(s)",
                details={
                    "message": message,
                    "success_count": success_count,
                    "failed_count": len(error_messages),
                    "total_webhooks": len(webhook_urls),
                    "results": results,
                },
            )

            if success_count > 0:
                response_message = f"Message sent to {success_count} webhook(s)"
                if error_messages:
                    response_message += f" ({len(error_messages)} failed)"
                return jsonify(
                    {
                        "success": True,
                        "message": response_message,
                        "success_count": success_count,
                        "failed_count": len(error_messages),
                        "results": results,
                    }
                )

            error_msg = "Failed to send to any webhook"
            if error_messages:
                error_msg = "; ".join(error_messages[:3])
            return (
                jsonify(
                    {
                        "success": False,
                        "error": error_msg,
                        "success_count": 0,
                        "failed_count": len(error_messages),
                        "results": results,
                    }
                ),
                500,
            )
        except Exception as e:
            logger.error(f"Error sending custom webhook message: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    return bp

