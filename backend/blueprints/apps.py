import requests
from flask import Blueprint, Response, jsonify, request


def create_apps_blueprint(
    storage,
    require_auth,
    load_apps,
    save_app,
    delete_app,
    parse_interval,
    validate_notification_destination,
    setup_scheduler,
    check_app,
    post_to_discord,
    fetch_app_info,
    logger,
):
    bp = Blueprint("apps_api", __name__)
    auth_required = require_auth(storage)

    @bp.route("/api/apps", methods=["GET"])
    @auth_required
    def get_apps():
        return jsonify(load_apps())

    @bp.route("/api/apps", methods=["POST"])
    @auth_required
    def create_app():
        if not request.json:
            return jsonify({"error": "Request body must be JSON"}), 400

        data = request.json
        required_fields = ["name", "app_store_id"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        name = str(data["name"]).strip()
        app_store_id = str(data["app_store_id"]).strip()
        app_store_country = str(data.get("app_store_country", "us")).strip().lower()

        if not name:
            return jsonify({"error": "App name cannot be empty"}), 400
        if not app_store_id or not app_store_id.isdigit():
            return jsonify({"error": "App Store ID must be a number"}), 400
        if len(app_store_country) != 2 or not app_store_country.isalpha():
            return jsonify({"error": "App Store country must be a 2-letter code (e.g., us, gb, in)"}), 400

        notification_destinations = data.get("notification_destinations", [])
        if not isinstance(notification_destinations, list):
            return jsonify({"error": "notification_destinations must be an array"}), 400

        current_settings = storage.get_settings()
        for dest in notification_destinations:
            is_valid, error_msg = validate_notification_destination(dest, current_settings)
            if not is_valid:
                return jsonify({"error": error_msg}), 400

        if not notification_destinations and "webhook_url" in data:
            webhook_url = str(data["webhook_url"]).strip()
            if webhook_url:
                if not webhook_url.startswith("https://discord.com/api/webhooks/"):
                    return jsonify({"error": "Invalid Discord webhook URL"}), 400
                notification_destinations = [{"type": "discord", "webhook_url": webhook_url}]

        interval_override = data.get("interval_override", "").strip() if data.get("interval_override") else None
        if interval_override:
            try:
                parse_interval(interval_override)
            except (ValueError, AttributeError):
                return jsonify({"error": "Invalid interval format. Use format like: 6h, 30m, 1d"}), 400

        app_data = {
            "name": name,
            "app_store_id": app_store_id,
            "app_store_country": app_store_country,
            "notification_destinations": notification_destinations,
            "interval_override": interval_override,
            "enabled": data.get("enabled", True),
        }

        if "icon_url" not in data or not data.get("icon_url"):
            try:
                app_info = fetch_app_info(app_store_id, app_store_country)
                if app_info and app_info.get("artworkUrl"):
                    app_data["icon_url"] = app_info["artworkUrl"]
            except Exception as e:
                logger.warning(f"Could not fetch icon for app {app_store_id}: {e}")
        else:
            app_data["icon_url"] = data.get("icon_url")

        try:
            app_id = save_app(app_data)
            setup_scheduler()
            storage.add_history_entry(
                event_type="app_created",
                app_id=app_id,
                app_name=name,
                status="success",
                message=f'App "{name}" created',
                details={"app_store_id": app_store_id, "enabled": app_data.get("enabled", True)},
            )
            return jsonify({"id": app_id, **app_data}), 201
        except Exception as e:
            logger.error(f"Error creating app: {e}", exc_info=True)
            storage.add_history_entry(
                event_type="app_created",
                app_name=name,
                status="error",
                message=f'Failed to create app "{name}"',
                details={"error": str(e)},
            )
            return jsonify({"error": "Failed to create app"}), 500

    @bp.route("/api/apps/<app_id>", methods=["PUT"])
    @auth_required
    def update_app(app_id):
        if not request.json:
            return jsonify({"error": "Request body must be JSON"}), 400

        data = request.json
        app = storage.get_app(app_id)
        if not app:
            return jsonify({"error": "App not found"}), 404

        if "name" in data:
            name = str(data["name"]).strip()
            if not name:
                return jsonify({"error": "App name cannot be empty"}), 400
            app["name"] = name

        if "app_store_id" in data:
            app_store_id = str(data["app_store_id"]).strip()
            if not app_store_id or not app_store_id.isdigit():
                return jsonify({"error": "App Store ID must be a number"}), 400
            app["app_store_id"] = app_store_id

        if "app_store_country" in data:
            app_store_country = str(data["app_store_country"]).strip().lower() if data["app_store_country"] else "us"
            if len(app_store_country) != 2 or not app_store_country.isalpha():
                return jsonify({"error": "App Store country must be a 2-letter code (e.g., us, gb, in)"}), 400
            app["app_store_country"] = app_store_country
        elif not app.get("app_store_country"):
            app["app_store_country"] = "us"

        if "notification_destinations" in data:
            notification_destinations = data["notification_destinations"]
            if not isinstance(notification_destinations, list):
                return jsonify({"error": "notification_destinations must be an array"}), 400

            current_settings = storage.get_settings()
            for dest in notification_destinations:
                is_valid, error_msg = validate_notification_destination(dest, current_settings)
                if not is_valid:
                    return jsonify({"error": error_msg}), 400

            app["notification_destinations"] = notification_destinations
        elif "webhook_url" in data:
            webhook_url = str(data["webhook_url"]).strip()
            if webhook_url:
                if not webhook_url.startswith("https://discord.com/api/webhooks/"):
                    return jsonify({"error": "Invalid Discord webhook URL"}), 400
                app["notification_destinations"] = [{"type": "discord", "webhook_url": webhook_url}]

        if "interval_override" in data:
            interval_override = data["interval_override"]
            if interval_override:
                interval_override = str(interval_override).strip()
                try:
                    parse_interval(interval_override)
                except (ValueError, AttributeError):
                    return jsonify({"error": "Invalid interval format. Use format like: 6h, 30m, 1d"}), 400
            app["interval_override"] = interval_override if interval_override else None

        if "enabled" in data:
            app["enabled"] = bool(data["enabled"])

        if "icon_url" in data:
            app["icon_url"] = data["icon_url"]
        elif "app_store_id" in data or "app_store_country" in data:
            try:
                app_info = fetch_app_info(app["app_store_id"], app.get("app_store_country", "us"))
                if app_info and app_info.get("artworkUrl"):
                    app["icon_url"] = app_info["artworkUrl"]
            except Exception as e:
                logger.warning(f"Could not fetch icon for app {app['app_store_id']}: {e}")

        try:
            app_name = app.get("name", "Unknown")
            save_app(app)
            setup_scheduler()
            storage.add_history_entry(
                event_type="app_updated",
                app_id=app_id,
                app_name=app_name,
                status="success",
                message=f'App "{app_name}" updated',
                details={"enabled": app.get("enabled", True)},
            )
            return jsonify(app)
        except Exception as e:
            logger.error(f"Error updating app {app_id}: {e}", exc_info=True)
            app_name = app.get("name", "Unknown") if "app" in locals() else "Unknown"
            storage.add_history_entry(
                event_type="app_updated",
                app_id=app_id,
                app_name=app_name,
                status="error",
                message=f'Failed to update app "{app_name}"',
                details={"error": str(e)},
            )
            return jsonify({"error": "Failed to update app"}), 500

    @bp.route("/api/apps/<app_id>", methods=["DELETE"])
    @auth_required
    def remove_app(app_id):
        app = storage.get_app(app_id)
        app_name = app.get("name", "Unknown") if app else "Unknown"
        if delete_app(app_id):
            setup_scheduler()
            storage.add_history_entry(
                event_type="app_deleted",
                app_id=app_id,
                app_name=app_name,
                status="success",
                message=f'App "{app_name}" deleted',
            )
            return jsonify({"message": "App deleted"}), 200
        return jsonify({"error": "App not found"}), 404

    @bp.route("/api/apps/<app_id>/check", methods=["POST"])
    @auth_required
    def check_app_endpoint(app_id):
        result, status_code = check_app(app_id)
        return jsonify(result), status_code

    @bp.route("/api/apps/<app_id>/post", methods=["POST"])
    @auth_required
    def post_app_endpoint(app_id):
        result, status_code = post_to_discord(app_id)
        return jsonify(result), status_code

    @bp.route("/api/apps/<app_id>/icon", methods=["GET"])
    @auth_required
    def get_app_icon(app_id):
        app = storage.get_app(app_id)
        if not app:
            return jsonify({"error": "App not found"}), 404
        icon_url = app.get("icon_url")
        if not icon_url or not icon_url.strip():
            return jsonify({"error": "No icon"}), 404
        try:
            resp = requests.get(icon_url, timeout=10, stream=True)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "image/png")
            if not content_type.startswith("image/"):
                content_type = "image/png"
            return Response(resp.iter_content(chunk_size=8192), mimetype=content_type)
        except Exception as e:
            logger.warning(f"Could not fetch icon for app {app_id}: {e}")
            return jsonify({"error": "Could not load icon"}), 404

    @bp.route("/api/apps/metadata/<app_store_id>", methods=["GET"])
    @auth_required
    def get_app_metadata(app_store_id):
        try:
            country = request.args.get("country", "us")
            app_info = fetch_app_info(app_store_id, country)
            if not app_info:
                return jsonify({"error": "App not found in App Store"}), 404
            return jsonify(
                {
                    "trackName": app_info.get("trackName"),
                    "artistName": app_info.get("artistName"),
                    "artworkUrl": app_info.get("artworkUrl"),
                    "version": app_info.get("version"),
                    "bundleId": app_info.get("bundleId"),
                }
            )
        except Exception as e:
            logger.error(f"Error fetching app metadata: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    return bp

