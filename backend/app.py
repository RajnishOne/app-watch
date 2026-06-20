#!/usr/bin/env python3
"""
App Watch - Main Application
"""
import os
import json
import logging
import threading
import time
from datetime import datetime
from functools import partial
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import schedule

from backend.app_store import AppStoreMonitor
from backend.blueprints.apps import create_apps_blueprint
from backend.blueprints.history import create_history_blueprint
from backend.blueprints.settings import create_settings_blueprint
from backend.blueprints.webhooks import create_webhooks_blueprint
from backend.formatter import DiscordFormatter
from backend.storage import StorageManager
from backend.version import get_version
from backend.auth import require_auth

# Application version - dynamically fetched
APP_VERSION = get_version()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CRA build layout: frontend/dist/index.html and frontend/dist/static/js|css/...
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
if not os.path.exists(frontend_dist):
    frontend_dist = None

# Flask static route must map URL /static/<file> to dist/static/<file>, not dist/<file>.
# static_url_path='' registers /<path:filename> and steals SPA paths like /scheduler.
flask_static_folder = (
    os.path.join(frontend_dist, 'static')
    if frontend_dist and os.path.isdir(os.path.join(frontend_dist, 'static'))
    else None
)
app = Flask(__name__, static_folder=flask_static_folder, static_url_path='/static')
# CORS - allow all origins for self-hosted use (restrict in production if needed)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize components
storage = StorageManager(Path(os.getenv('DATA_DIR', '/data')))
# Load settings for formatter and notification handler
settings = storage.get_settings()
formatter = DiscordFormatter(settings)
monitor = AppStoreMonitor(storage, formatter, settings)

# Global scheduler thread
scheduler_thread = None
scheduler_running = False


def scheduler_is_disabled():
    """Allow tests and constrained environments to opt out of scheduler threads."""
    return os.getenv('DISABLE_SCHEDULER', '').lower() in {'1', 'true', 'yes'}


def load_apps():
    """Load apps from storage"""
    return storage.get_all_apps()


def save_app(app_data):
    """Save app to storage"""
    return storage.save_app(app_data)


def delete_app(app_id):
    """Delete app from storage"""
    return storage.delete_app(app_id)


def get_default_interval():
    """Get default check interval from settings or environment"""
    try:
        settings = storage.get_settings()
        interval_str = settings.get('default_interval', os.getenv('CHECK_INTERVAL', '12h'))
    except Exception as e:
        logger.warning(f"Error reading settings, falling back to environment: {e}")
        interval_str = os.getenv('CHECK_INTERVAL', '12h')
    return parse_interval(interval_str)


def parse_interval(interval_str):
    """Parse interval string like '12h', '30m', '1d' to seconds"""
    if not interval_str:
        raise ValueError("Interval string cannot be empty")
    
    interval_str = str(interval_str).lower().strip()
    
    if not interval_str:
        raise ValueError("Interval string cannot be empty")
    
    try:
        if interval_str.endswith('h'):
            hours = int(interval_str[:-1])
            if hours <= 0:
                raise ValueError("Hours must be positive")
            return hours * 3600
        elif interval_str.endswith('m'):
            minutes = int(interval_str[:-1])
            if minutes <= 0:
                raise ValueError("Minutes must be positive")
            return minutes * 60
        elif interval_str.endswith('d'):
            days = int(interval_str[:-1])
            if days <= 0:
                raise ValueError("Days must be positive")
            return days * 86400
        else:
            # Assume seconds if no suffix
            seconds = int(interval_str)
            if seconds <= 0:
                raise ValueError("Seconds must be positive")
            return seconds
    except ValueError as e:
        if "invalid literal" in str(e).lower():
            raise ValueError(f"Invalid interval format: {interval_str}. Use format like: 6h, 30m, 1d")
        raise


def format_interval(seconds):
    """Format seconds to interval string"""
    if seconds >= 86400:
        return f"{seconds // 86400}d"
    elif seconds >= 3600:
        return f"{seconds // 3600}h"
    elif seconds >= 60:
        return f"{seconds // 60}m"
    else:
        return f"{seconds}s"


def validate_notification_destination(dest, settings=None):
    """
    Validate a notification destination
    
    Returns: (is_valid: bool, error_message: Optional[str])
    """
    if not isinstance(dest, dict):
        return False, 'Each notification destination must be an object'
    
    dest_type = dest.get('type', '').lower().strip()
    if not dest_type:
        return False, 'Each notification destination must have a type'
    
    settings = settings or {}
    
    if dest_type == 'discord':
        webhook_url = dest.get('webhook_url', '').strip()
        if not webhook_url:
            return False, 'Discord destination requires webhook_url'
        if not webhook_url.startswith('https://discord.com/api/webhooks/'):
            return False, 'Invalid Discord webhook URL'
        return True, None
    
    elif dest_type == 'slack':
        webhook_url = dest.get('webhook_url', '').strip()
        if not webhook_url:
            return False, 'Slack destination requires webhook_url'
        if not webhook_url.startswith('https://hooks.slack.com/'):
            return False, 'Invalid Slack webhook URL'
        return True, None
    
    elif dest_type == 'telegram':
        chat_id = dest.get('chat_id', '').strip()
        bot_token = dest.get('bot_token', '').strip() or settings.get('telegram_bot_token', '').strip()
        if not bot_token:
            return False, 'Telegram destination requires bot_token (set in destination or settings)'
        if not chat_id:
            return False, 'Telegram destination requires chat_id'
        return True, None
    
    elif dest_type == 'teams':
        webhook_url = dest.get('webhook_url', '').strip()
        if not webhook_url:
            return False, 'Microsoft Teams destination requires webhook_url'
        if not webhook_url.startswith('https://'):
            return False, 'Invalid Microsoft Teams webhook URL (must be HTTPS)'
        return True, None
    
    elif dest_type == 'email':
        email = dest.get('email', '').strip()
        if not email:
            return False, 'Email destination requires email address'
        # Basic email validation
        if '@' not in email or '.' not in email.split('@')[1]:
            return False, 'Invalid email address format'
        
        # Check if SMTP settings are available (either in dest or settings)
        smtp_host = dest.get('smtp_host', '').strip() or settings.get('smtp_host', '').strip()
        if not smtp_host:
            return False, 'Email destination requires SMTP host (set in destination or settings)'
        return True, None
    
    elif dest_type == 'generic':
        webhook_url = dest.get('webhook_url', '').strip()
        if not webhook_url:
            return False, 'Generic webhook destination requires webhook_url'
        if not webhook_url.startswith('http://') and not webhook_url.startswith('https://'):
            return False, 'Invalid webhook URL (must start with http:// or https://)'
        
        # Validate payload_template if provided (must be valid JSON)
        payload_template = dest.get('payload_template', '').strip()
        if payload_template:
            try:
                import json
                json.loads(payload_template)
            except json.JSONDecodeError:
                return False, 'Invalid JSON in payload_template'
        
        return True, None
    
    else:
        return False, f'Unknown notification type: {dest_type}'


def check_app(app_id):
    """Check a single app for updates"""
    try:
        app = storage.get_app(app_id)
        if not app:
            return {'error': 'App not found'}, 404
        
        if not app.get('enabled', True):
            return {'message': 'App is disabled'}, 200
        
        # Ensure monitor has latest settings (in case they changed)
        global monitor, formatter
        current_settings = storage.get_settings()
        if monitor.settings != current_settings:
            logger.debug("Reloading monitor with updated settings")
            formatter = DiscordFormatter(current_settings)
            monitor = AppStoreMonitor(storage, formatter, current_settings)
        
        app_name = app.get('name', 'Unknown')
        result = monitor.check_app(app)
        
        # Log check result
        if result.get('success'):
            if result.get('current_version') and result.get('last_version') and result.get('current_version') != result.get('last_version'):
                # New version detected
                storage.add_history_entry(
                    event_type='check',
                    app_id=app_id,
                    app_name=app_name,
                    status='success',
                    message=f'New version detected: {result.get("current_version")}',
                    details={'version': result.get('current_version'), 'previous_version': result.get('last_version')}
                )
            else:
                # No update
                storage.add_history_entry(
                    event_type='check',
                    app_id=app_id,
                    app_name=app_name,
                    status='info',
                    message='No new version available',
                    details={'version': result.get('current_version')}
                )
        else:
            # Check failed
            storage.add_history_entry(
                event_type='check',
                app_id=app_id,
                app_name=app_name,
                status='error',
                message=f'Check failed: {result.get("error", "Unknown error")}',
                details={'error': result.get('error')}
            )
        
        return result, 200
    except Exception as e:
        logger.error(f"Error checking app {app_id}: {e}", exc_info=True)
        app = storage.get_app(app_id) if app_id else None
        app_name = app.get('name', 'Unknown') if app else 'Unknown'
        storage.add_history_entry(
            event_type='check',
            app_id=app_id,
            app_name=app_name,
            status='error',
            message=f'Check error: {str(e)}',
            details={'error': str(e)}
        )
        return {'error': str(e)}, 500


def post_to_discord(app_id):
    """Manually post current release notes to all configured notification destinations"""
    try:
        app = storage.get_app(app_id)
        if not app:
            return {'error': 'App not found'}, 404
        
        app_name = app.get('name', 'Unknown')
        result = monitor.post_to_discord(app)
        
        # Log post result
        if result.get('success'):
            storage.add_history_entry(
                event_type='post',
                app_id=app_id,
                app_name=app_name,
                status='success',
                message=result.get('message', 'Posted successfully'),
                details={'version': result.get('version'), 'message': result.get('message')}
            )
        else:
            storage.add_history_entry(
                event_type='post',
                app_id=app_id,
                app_name=app_name,
                status='error',
                message=f'Post failed: {result.get("error", "Unknown error")}',
                details={'error': result.get('error'), 'version': result.get('version')}
            )
        
        return result, 200
    except Exception as e:
        logger.error(f"Error posting to notification destinations for app {app_id}: {e}", exc_info=True)
        app = storage.get_app(app_id) if app_id else None
        app_name = app.get('name', 'Unknown') if app else 'Unknown'
        storage.add_history_entry(
            event_type='post',
            app_id=app_id,
            app_name=app_name,
            status='error',
            message=f'Post error: {str(e)}',
            details={'error': str(e)}
        )
        return {'error': str(e)}, 500


def fetch_app_info(app_store_id, country='us', platform='ios'):
    """Proxy through current monitor instance (supports runtime monitor reload)."""
    if platform == 'android':
        return monitor.fetch_android_app_info(app_store_id, country)
    return monitor.fetch_app_info(app_store_id, country)


def reload_monitor(current_settings=None):
    """Reload monitor and formatter with current settings."""
    global monitor, formatter
    settings_obj = current_settings if current_settings is not None else storage.get_settings()
    formatter = DiscordFormatter(settings_obj)
    monitor = AppStoreMonitor(storage, formatter, settings_obj)


def run_scheduler():
    """Run the scheduler loop"""
    global scheduler_running
    scheduler_running = True
    logger.info("Scheduler loop started")
    
    while scheduler_running:
        try:
            schedule.run_pending()
        except Exception as e:
            logger.error(f"Error running scheduled job: {e}", exc_info=True)
        time.sleep(60)  # Check every minute
    
    logger.info("Scheduler loop stopped")


def setup_scheduler():
    """Setup scheduled checks for all apps"""
    global scheduler_thread

    if scheduler_is_disabled():
        logger.info("Scheduler initialization skipped (DISABLE_SCHEDULER enabled)")
        return
    
    # Clear existing jobs
    schedule.clear()
    logger.info("Cleared existing scheduled jobs")
    
    apps = load_apps()
    default_interval = get_default_interval()
    
    scheduled_count = 0
    for app in apps:
        if not app.get('enabled', True):
            logger.debug(f"Skipping disabled app: {app.get('name', 'Unknown')}")
            continue
        
        app_id = app['app_store_id']
        app_uuid = app['id']  # Use the UUID, not app_store_id
        app_name = app.get('name', 'Unknown')
        interval_override = app.get('interval_override')
        interval_seconds = parse_interval(interval_override) if interval_override else default_interval
        interval_str = format_interval(interval_seconds)
        
        # Schedule job - use functools.partial to properly capture app_id
        # Wrap in a function to handle errors properly
        def make_scheduled_check(app_uuid_to_check, app_name_to_log, interval_str):
            def scheduled_check():
                try:
                    logger.debug(f"Running scheduled check for app {app_uuid_to_check}")
                    # Log scheduler run
                    app_for_log = storage.get_app(app_uuid_to_check)
                    app_name = app_for_log.get('name', 'Unknown') if app_for_log else app_name_to_log
                    storage.add_history_entry(
                        event_type='scheduler_run',
                        app_id=app_uuid_to_check,
                        app_name=app_name,
                        status='info',
                        message=f'Scheduled check triggered (interval: {interval_str})',
                        details={'interval': interval_str, 'triggered_by': 'scheduler'}
                    )
                    result, status_code = check_app(app_uuid_to_check)
                    logger.debug(f"Scheduled check completed for app {app_uuid_to_check}: {result.get('message', 'Unknown')}")
                except Exception as e:
                    logger.error(f"Error in scheduled check for app {app_uuid_to_check}: {e}", exc_info=True)
                    # Log scheduler error
                    app_for_log = storage.get_app(app_uuid_to_check)
                    app_name = app_for_log.get('name', 'Unknown') if app_for_log else app_name_to_log
                    storage.add_history_entry(
                        event_type='scheduler_run',
                        app_id=app_uuid_to_check,
                        app_name=app_name,
                        status='error',
                        message=f'Scheduled check failed: {str(e)}',
                        details={'interval': interval_str, 'triggered_by': 'scheduler', 'error': str(e)}
                    )
            return scheduled_check
        
        schedule.every(interval_seconds).seconds.do(make_scheduled_check(app_uuid, app_name, interval_str))
        scheduled_count += 1
        logger.info(f"Scheduled app {app['name']} ({app_id}) to check every {format_interval(interval_seconds)}")
    
    logger.info(f"Total apps scheduled: {scheduled_count}")
    
    # Start scheduler thread if not running
    if scheduler_thread is None or not scheduler_thread.is_alive():
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Scheduler thread started")
    else:
        logger.info("Scheduler thread already running")


# API Routes

# Authentication endpoints (public)
@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    """Return API key for settings; user login is not used."""
    auth = storage.get_auth()
    return jsonify({
        'enabled': False,
        'configured': True,
        'auth_type': auth.get('auth_type', 'forms'),
        'bypass_local_networks': False,
        'api_key': auth.get('api_key', ''),
    })


@app.route('/api/auth/api-key/regenerate', methods=['POST'])
@require_auth(storage)
def regenerate_api_key():
    """Regenerate API key"""
    try:
        new_key = storage.regenerate_api_key()
        return jsonify({
            'api_key': new_key,
            'message': 'API key regenerated successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error regenerating API key: {e}", exc_info=True)
        return jsonify({'error': 'Failed to regenerate API key'}), 500


@app.route('/health', methods=['GET'])
def health():
    """Liveness probe: no auth, disk I/O, or scheduler work — safe for frequent checks."""
    return jsonify({'status': 'ok'}), 200


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve frontend - handle SPA routing"""
    # Don't handle API routes here - they're defined above
    if path.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404
    
    if frontend_dist and os.path.exists(os.path.join(frontend_dist, 'index.html')):
        # Serve root assets (favicon, manifest, …) and CRA files under dist/static/...
        if path:
            file_path = os.path.join(frontend_dist, path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return send_from_directory(frontend_dist, path)

        return send_from_directory(frontend_dist, 'index.html')
    else:
        return jsonify({'message': 'Frontend not built. Please build the frontend first.'}), 503


@app.route('/api/status', methods=['GET'])
@require_auth(storage)
def status():
    """Health check endpoint"""
    global scheduler_thread
    
    # Check if scheduler thread is alive, restart if needed
    scheduler_alive = scheduler_thread is not None and scheduler_thread.is_alive()
    if not scheduler_alive and scheduler_running:
        logger.warning("Scheduler thread died, restarting...")
        try:
            setup_scheduler()
        except Exception as e:
            logger.error(f"Failed to restart scheduler: {e}", exc_info=True)
    
    return jsonify({
        'status': 'ok',
        'version': APP_VERSION,
        'timestamp': datetime.now().isoformat(),
        'scheduler_running': scheduler_running,
        'scheduler_thread_alive': scheduler_alive,
        'scheduled_jobs_count': len(schedule.jobs)
    })


app.register_blueprint(
    create_apps_blueprint(
        storage=storage,
        require_auth=require_auth,
        load_apps=load_apps,
        save_app=save_app,
        delete_app=delete_app,
        parse_interval=parse_interval,
        validate_notification_destination=validate_notification_destination,
        setup_scheduler=setup_scheduler,
        check_app=check_app,
        post_to_discord=post_to_discord,
        fetch_app_info=fetch_app_info,
        logger=logger,
    )
)

app.register_blueprint(
    create_webhooks_blueprint(
        storage=storage,
        require_auth=require_auth,
        load_apps=load_apps,
        logger=logger,
    )
)

app.register_blueprint(
    create_history_blueprint(
        storage=storage,
        require_auth=require_auth,
        logger=logger,
    )
)

app.register_blueprint(
    create_settings_blueprint(
        storage=storage,
        require_auth=require_auth,
        parse_interval=parse_interval,
        setup_scheduler=setup_scheduler,
        app_version=APP_VERSION,
        reload_monitor=reload_monitor,
        logger=logger,
    )
)


# Initialize scheduler when module loads
# Wrap in try-except to handle errors gracefully
try:
    setup_scheduler()
except Exception as e:
    logger.error(f"Failed to initialize scheduler: {e}", exc_info=True)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8192))
    # Use production WSGI server in production (gunicorn recommended)
    # For self-hosted, Flask dev server is acceptable
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

