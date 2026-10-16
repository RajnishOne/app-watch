from flask import Blueprint, jsonify, request
from backend.notification_profiles import validate_notification_profiles


def create_settings_blueprint(
    storage,
    require_auth,
    parse_interval,
    setup_scheduler,
    app_version,
    reload_monitor,
    validate_notification_destination,
    logger,
):
    bp = Blueprint("settings_api", __name__)
    auth_required = require_auth(storage)

    @bp.route("/api/settings", methods=["GET"])
    @auth_required
    def get_settings():
        try:
            settings = storage.get_settings()
            settings["version"] = app_version
            return jsonify(settings)
        except Exception as e:
            logger.error(f"Error getting settings: {e}", exc_info=True)
            return jsonify({"error": "Failed to get settings"}), 500

    @bp.route("/api/settings", methods=["PUT"])
    @auth_required
    def update_settings():
        if not request.json:
            return jsonify({"error": "Request body must be JSON"}), 400

        data = request.json
        if "default_interval" in data:
            interval = data["default_interval"]
            if interval:
                try:
                    parse_interval(interval)
                except (ValueError, AttributeError):
                    return jsonify({"error": "Invalid interval format. Use format like: 6h, 30m, 1d"}), 400

        try:
            current_settings = storage.get_settings()
            current_settings.update(data)
            is_valid, error = validate_notification_profiles(
                current_settings.get("notification_profiles", []),
                current_settings,
                validate_notification_destination,
            )
            if not is_valid:
                return jsonify({"error": error}), 400

            storage.save_settings(current_settings)

            if "default_interval" in data:
                setup_scheduler()

            reload_monitor(current_settings)
            setup_scheduler()
            return jsonify(current_settings)
        except Exception as e:
            logger.error(f"Error updating settings: {e}", exc_info=True)
            return jsonify({"error": "Failed to update settings"}), 500

    return bp

