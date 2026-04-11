from flask import Blueprint, jsonify, request


def create_history_blueprint(storage, require_auth, logger):
    bp = Blueprint("history_api", __name__)
    auth_required = require_auth(storage)

    @bp.route("/api/logs", methods=["GET"])
    @auth_required
    def get_logs():
        return jsonify({"logs": []})

    @bp.route("/api/history", methods=["GET"])
    @auth_required
    def get_history():
        try:
            limit = request.args.get("limit", default=100, type=int)
            event_type = request.args.get("event_type", default=None, type=str)
            app_id = request.args.get("app_id", default=None, type=str)
            status = request.args.get("status", default=None, type=str)
            start_date = request.args.get("start_date", default=None, type=str)
            end_date = request.args.get("end_date", default=None, type=str)

            if limit < 1 or limit > 1000:
                limit = 100

            history = storage.get_history(
                limit=limit,
                event_type=event_type,
                app_id=app_id,
                status=status,
                start_date=start_date,
                end_date=end_date,
            )
            return jsonify({"history": history, "count": len(history)})
        except Exception as e:
            logger.error(f"Error getting history: {e}", exc_info=True)
            return jsonify({"error": "Failed to get history"}), 500

    return bp

