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
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import requests
import schedule

from backend.app_store import AppStoreMonitor
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

# Determine static folder path
static_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
if not os.path.exists(static_folder):
    static_folder = None

app = Flask(__name__, static_folder=static_folder, static_url_path='')
# CORS - allow all origins for self-hosted use (restrict in production if needed)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize components
storage = StorageManager(Path('/data'))
# Load settings for formatter and notification handler
settings = storage.get_settings()
formatter = DiscordFormatter(settings)
monitor = AppStoreMonitor(storage, formatter, settings)

# Global scheduler thread
scheduler_thread = None
scheduler_running = False


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
    
    if static_folder and os.path.exists(os.path.join(static_folder, 'index.html')):
        # Serve static files if they exist
        if path:
            static_path = os.path.join(static_folder, path)
            if os.path.exists(static_path) and os.path.isfile(static_path):
                return send_from_directory(static_folder, path)
        
        # Fallback to index.html for SPA routing
        return send_from_directory(static_folder, 'index.html')
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


@app.route('/api/apps', methods=['GET'])
@require_auth(storage)
def get_apps():
    """Get all apps"""
    apps = load_apps()
    return jsonify(apps)


@app.route('/api/apps', methods=['POST'])
@require_auth(storage)
def create_app():
    """Create a new app"""
    if not request.json:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    data = request.json
    
    required_fields = ['name', 'app_store_id']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Input validation
    name = str(data['name']).strip()
    app_store_id = str(data['app_store_id']).strip()
    
    if not name:
        return jsonify({'error': 'App name cannot be empty'}), 400
    if not app_store_id or not app_store_id.isdigit():
        return jsonify({'error': 'App Store ID must be a number'}), 400
    
    # Validate notification destinations if provided
    notification_destinations = data.get('notification_destinations', [])
    if not isinstance(notification_destinations, list):
        return jsonify({'error': 'notification_destinations must be an array'}), 400
    
    # Validate each destination
    current_settings = storage.get_settings()
    for dest in notification_destinations:
        is_valid, error_msg = validate_notification_destination(dest, current_settings)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
    
    # Legacy support - if webhook_url is provided but no notification_destinations, convert it
    if not notification_destinations and 'webhook_url' in data:
        webhook_url = str(data['webhook_url']).strip()
        if webhook_url:
            if not webhook_url.startswith('https://discord.com/api/webhooks/'):
                return jsonify({'error': 'Invalid Discord webhook URL'}), 400
            notification_destinations = [{'type': 'discord', 'webhook_url': webhook_url}]
    
    # Validate interval if provided
    interval_override = data.get('interval_override', '').strip() if data.get('interval_override') else None
    if interval_override:
        try:
            parse_interval(interval_override)
        except (ValueError, AttributeError):
            return jsonify({'error': 'Invalid interval format. Use format like: 6h, 30m, 1d'}), 400
    
    app_data = {
        'name': name,
        'app_store_id': app_store_id,
        'notification_destinations': notification_destinations,
        'interval_override': interval_override,
        'enabled': data.get('enabled', True)
    }
    
    # Try to fetch and save icon URL if not provided
    if 'icon_url' not in data or not data.get('icon_url'):
        try:
            app_info = monitor.fetch_app_info(app_store_id)
            if app_info and app_info.get('artworkUrl'):
                app_data['icon_url'] = app_info['artworkUrl']
        except Exception as e:
            logger.warning(f"Could not fetch icon for app {app_store_id}: {e}")
    else:
        app_data['icon_url'] = data.get('icon_url')
    
    try:
        app_id = save_app(app_data)
        setup_scheduler()  # Reschedule
        # Log app creation
        storage.add_history_entry(
            event_type='app_created',
            app_id=app_id,
            app_name=name,
            status='success',
            message=f'App "{name}" created',
            details={'app_store_id': app_store_id, 'enabled': app_data.get('enabled', True)}
        )
        return jsonify({'id': app_id, **app_data}), 201
    except Exception as e:
        logger.error(f"Error creating app: {e}", exc_info=True)
        storage.add_history_entry(
            event_type='app_created',
            app_name=name,
            status='error',
            message=f'Failed to create app "{name}"',
            details={'error': str(e)}
        )
        return jsonify({'error': 'Failed to create app'}), 500


@app.route('/api/apps/<app_id>', methods=['PUT'])
@require_auth(storage)
def update_app(app_id):
    """Update an app"""
    if not request.json:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    data = request.json
    
    app = storage.get_app(app_id)
    if not app:
        return jsonify({'error': 'App not found'}), 404
    
    # Update fields with validation
    if 'name' in data:
        name = str(data['name']).strip()
        if not name:
            return jsonify({'error': 'App name cannot be empty'}), 400
        app['name'] = name
    
    if 'app_store_id' in data:
        app_store_id = str(data['app_store_id']).strip()
        if not app_store_id or not app_store_id.isdigit():
            return jsonify({'error': 'App Store ID must be a number'}), 400
        app['app_store_id'] = app_store_id
    
    # Handle notification destinations
    if 'notification_destinations' in data:
        notification_destinations = data['notification_destinations']
        if not isinstance(notification_destinations, list):
            return jsonify({'error': 'notification_destinations must be an array'}), 400
        
        # Validate each destination
        current_settings = storage.get_settings()
        for dest in notification_destinations:
            is_valid, error_msg = validate_notification_destination(dest, current_settings)
            if not is_valid:
                return jsonify({'error': error_msg}), 400
        
        app['notification_destinations'] = notification_destinations
    
    # Legacy support - if webhook_url is provided, convert it
    elif 'webhook_url' in data:
        webhook_url = str(data['webhook_url']).strip()
        if webhook_url:
            if not webhook_url.startswith('https://discord.com/api/webhooks/'):
                return jsonify({'error': 'Invalid Discord webhook URL'}), 400
            app['notification_destinations'] = [{'type': 'discord', 'webhook_url': webhook_url}]
    
    if 'interval_override' in data:
        interval_override = data['interval_override']
        if interval_override:
            interval_override = str(interval_override).strip()
            try:
                parse_interval(interval_override)
            except (ValueError, AttributeError):
                return jsonify({'error': 'Invalid interval format. Use format like: 6h, 30m, 1d'}), 400
        app['interval_override'] = interval_override if interval_override else None
    
    if 'enabled' in data:
        app['enabled'] = bool(data['enabled'])
    
    # Handle icon URL update
    if 'icon_url' in data:
        app['icon_url'] = data['icon_url']
    elif 'app_store_id' in data:
        # If app_store_id changed, try to fetch new icon
        try:
            app_info = monitor.fetch_app_info(app['app_store_id'])
            if app_info and app_info.get('artworkUrl'):
                app['icon_url'] = app_info['artworkUrl']
        except Exception as e:
            logger.warning(f"Could not fetch icon for app {app['app_store_id']}: {e}")
    
    try:
        app_name = app.get('name', 'Unknown')
        save_app(app)
        setup_scheduler()  # Reschedule
        # Log app update
        storage.add_history_entry(
            event_type='app_updated',
            app_id=app_id,
            app_name=app_name,
            status='success',
            message=f'App "{app_name}" updated',
            details={'enabled': app.get('enabled', True)}
        )
        return jsonify(app)
    except Exception as e:
        logger.error(f"Error updating app {app_id}: {e}", exc_info=True)
        app_name = app.get('name', 'Unknown') if 'app' in locals() else 'Unknown'
        storage.add_history_entry(
            event_type='app_updated',
            app_id=app_id,
            app_name=app_name,
            status='error',
            message=f'Failed to update app "{app_name}"',
            details={'error': str(e)}
        )
        return jsonify({'error': 'Failed to update app'}), 500


@app.route('/api/apps/<app_id>', methods=['DELETE'])
@require_auth(storage)
def remove_app(app_id):
    """Delete an app"""
    app = storage.get_app(app_id)
    app_name = app.get('name', 'Unknown') if app else 'Unknown'
    
    if delete_app(app_id):
        setup_scheduler()  # Reschedule
        # Log app deletion
        storage.add_history_entry(
            event_type='app_deleted',
            app_id=app_id,
            app_name=app_name,
            status='success',
            message=f'App "{app_name}" deleted'
        )
        return jsonify({'message': 'App deleted'}), 200
    else:
        return jsonify({'error': 'App not found'}), 404


@app.route('/api/apps/<app_id>/check', methods=['POST'])
@require_auth(storage)
def check_app_endpoint(app_id):
    """Manually check an app for updates"""
    result, status_code = check_app(app_id)
    return jsonify(result), status_code


@app.route('/api/apps/<app_id>/post', methods=['POST'])
@require_auth(storage)
def post_app_endpoint(app_id):
    """Manually post release notes to all configured notification destinations"""
    result, status_code = post_to_discord(app_id)
    return jsonify(result), status_code


@app.route('/api/apps/<app_id>/icon', methods=['GET'])
@require_auth(storage)
def get_app_icon(app_id):
    """Serve app icon from stored icon_url (proxied from server to avoid client using Apple URLs)."""
    app = storage.get_app(app_id)
    if not app:
        return jsonify({'error': 'App not found'}), 404
    icon_url = app.get('icon_url')
    if not icon_url or not icon_url.strip():
        return jsonify({'error': 'No icon'}), 404
    try:
        resp = requests.get(icon_url, timeout=10, stream=True)
        resp.raise_for_status()
        content_type = resp.headers.get('Content-Type', 'image/png')
        # Restrict to image types
        if not content_type.startswith('image/'):
            content_type = 'image/png'
        return Response(resp.iter_content(chunk_size=8192), mimetype=content_type)
    except Exception as e:
        logger.warning(f"Could not fetch icon for app {app_id}: {e}")
        return jsonify({'error': 'Could not load icon'}), 404


@app.route('/api/webhooks/list', methods=['GET'])
@require_auth(storage)
def list_webhooks():
    """Get all webhooks from all apps for selection"""
    try:
        apps = load_apps()
        webhooks = []
        
        for app in apps:
            app_name = app.get('name', 'Unknown')
            notification_destinations = app.get('notification_destinations', [])
            
            # Support legacy webhook_url
            if not notification_destinations and app.get('webhook_url'):
                notification_destinations = [{
                    'type': 'discord',
                    'webhook_url': app['webhook_url']
                }]
            
            for dest in notification_destinations:
                dest_type = dest.get('type', '').lower()
                webhook_url = dest.get('webhook_url', '').strip()
                
                # Only include webhook-based destinations
                if dest_type in ['discord', 'slack', 'teams', 'generic'] and webhook_url:
                    webhooks.append({
                        'id': f"{app['id']}_{len(webhooks)}",
                        'app_name': app_name,
                        'app_id': app['id'],
                        'type': dest_type,
                        'webhook_url': webhook_url,
                        'label': f"{app_name} - {dest_type.capitalize()}"
                    })
        
        return jsonify({'webhooks': webhooks})
    except Exception as e:
        logger.error(f"Error listing webhooks: {e}", exc_info=True)
        return jsonify({'error': 'Failed to list webhooks'}), 500


@app.route('/api/webhooks/send', methods=['POST'])
@require_auth(storage)
def send_custom_webhook():
    """Send custom message to webhook(s)"""
    if not request.json:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    data = request.json
    message = data.get('message', '').strip()
    webhook_urls = data.get('webhook_urls', [])
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    if not webhook_urls or not isinstance(webhook_urls, list) or len(webhook_urls) == 0:
        return jsonify({'error': 'At least one webhook URL is required'}), 400
    
    # Validate webhook URLs
    for url in webhook_urls:
        if not isinstance(url, str) or not url.strip():
            return jsonify({'error': 'Invalid webhook URL'}), 400
        if not url.startswith('http://') and not url.startswith('https://'):
            return jsonify({'error': 'Webhook URL must start with http:// or https://'}), 400
    
    try:
        success_count = 0
        error_messages = []
        results = []
        
        for webhook_url in webhook_urls:
            webhook_url = webhook_url.strip()
            
            # Determine webhook type from URL
            webhook_type = 'generic'
            if webhook_url.startswith('https://discord.com/api/webhooks/'):
                webhook_type = 'discord'
            elif webhook_url.startswith('https://hooks.slack.com/'):
                webhook_type = 'slack'
            elif 'office.com' in webhook_url or 'office365' in webhook_url:
                webhook_type = 'teams'
            
            # Create destination object
            destination = {
                'type': webhook_type,
                'webhook_url': webhook_url
            }
            
            # Send message using NotificationHandler
            # For custom messages, we'll send the message directly as content
            success, error_msg = send_custom_message_to_webhook(destination, message, webhook_type)
            
            if success:
                success_count += 1
                results.append({'webhook_url': webhook_url, 'status': 'success'})
            else:
                error_messages.append(f"{webhook_url}: {error_msg or 'Failed'}")
                results.append({'webhook_url': webhook_url, 'status': 'error', 'error': error_msg})
        
        # Log the broadcast
        storage.add_history_entry(
            event_type='webhook_broadcast',
            app_id=None,
            app_name='Custom Message',
            status='success' if success_count > 0 else 'error',
            message=f'Custom message sent to {success_count} webhook(s)',
            details={
                'message': message,
                'success_count': success_count,
                'failed_count': len(error_messages),
                'total_webhooks': len(webhook_urls),
                'results': results
            }
        )
        
        if success_count > 0:
            response_message = f'Message sent to {success_count} webhook(s)'
            if error_messages:
                response_message += f' ({len(error_messages)} failed)'
            return jsonify({
                'success': True,
                'message': response_message,
                'success_count': success_count,
                'failed_count': len(error_messages),
                'results': results
            })
        else:
            error_msg = 'Failed to send to any webhook'
            if error_messages:
                error_msg = '; '.join(error_messages[:3])  # Limit error messages
            return jsonify({
                'success': False,
                'error': error_msg,
                'success_count': 0,
                'failed_count': len(error_messages),
                'results': results
            }), 500
            
    except Exception as e:
        logger.error(f"Error sending custom webhook message: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def send_custom_message_to_webhook(destination, message, webhook_type):
    """Send custom message to a webhook destination"""
    webhook_url = destination.get('webhook_url', '').strip()
    if not webhook_url:
        return False, 'Webhook URL is required'
    
    try:
        if webhook_type == 'discord':
            payload = {'content': message}
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True, None
        elif webhook_type == 'slack':
            payload = {'text': message}
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True, None
        elif webhook_type == 'teams':
            payload = {
                '@type': 'MessageCard',
                '@context': 'https://schema.org/extensions',
                'summary': 'Custom Message',
                'themeColor': '0078D4',
                'title': 'Custom Message',
                'text': message
            }
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True, None
        else:  # generic
            payload = {'message': message, 'content': message}
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True, None
    except requests.exceptions.ConnectionError as e:
        error_str = str(e).lower()
        if 'name resolution' in error_str or 'failed to resolve' in error_str or 'dns' in error_str:
            logger.error(f"DNS resolution error for webhook {webhook_url}: {e}")
            return False, 'Network error: Unable to resolve webhook hostname. Please check your internet connection and DNS settings.'
        elif 'connection refused' in error_str or 'connection timeout' in error_str:
            logger.error(f"Connection error for webhook {webhook_url}: {e}")
            return False, 'Connection error: Unable to connect to webhook server. Please check the webhook URL and your network connection.'
        else:
            logger.error(f"Connection error for webhook {webhook_url}: {e}")
            return False, 'Connection error: Unable to reach webhook server. Please check your network connection.'
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout error for webhook {webhook_url}: {e}")
        return False, 'Request timeout: The webhook server did not respond in time. Please try again later.'
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error for webhook {webhook_url}: {e}")
        status_code = e.response.status_code if hasattr(e, 'response') and e.response else None
        if status_code == 404:
            return False, 'Webhook not found (404). Please verify the webhook URL is correct.'
        elif status_code == 401 or status_code == 403:
            return False, 'Webhook authentication failed. Please verify the webhook URL is valid and not expired.'
        elif status_code == 429:
            return False, 'Rate limit exceeded. Please wait a moment before trying again.'
        else:
            return False, f'HTTP error ({status_code or "unknown"}): Webhook server returned an error.'
    except requests.exceptions.RequestException as e:
        logger.error(f"Error posting to webhook {webhook_url}: {e}")
        # Provide a cleaner error message
        error_str = str(e)
        if 'HTTPSConnectionPool' in error_str or 'HTTPConnectionPool' in error_str:
            # Extract the actual error message
            if 'Caused by' in error_str:
                error_str = error_str.split('Caused by')[-1].strip()
            else:
                # Try to extract meaningful part
                parts = error_str.split(':')
                if len(parts) > 1:
                    error_str = parts[-1].strip()
        return False, f'Failed to send message: {error_str}'


@app.route('/api/apps/metadata/<app_store_id>', methods=['GET'])
@require_auth(storage)
def get_app_metadata(app_store_id):
    """Fetch app metadata from App Store including icon"""
    try:
        app_info = monitor.fetch_app_info(app_store_id)
        if not app_info:
            return jsonify({'error': 'App not found in App Store'}), 404
        
        return jsonify({
            'trackName': app_info.get('trackName'),
            'artistName': app_info.get('artistName'),
            'artworkUrl': app_info.get('artworkUrl'),
            'version': app_info.get('version'),
            'bundleId': app_info.get('bundleId')
        })
    except Exception as e:
        logger.error(f"Error fetching app metadata: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/logs', methods=['GET'])
@require_auth(storage)
def get_logs():
    """Get recent logs (simplified - in production use proper log aggregation)"""
    # For now, return empty. In production, you'd read from log files
    return jsonify({'logs': []})


@app.route('/api/history', methods=['GET'])
@require_auth(storage)
def get_history():
    """Get activity history with optional filtering"""
    try:
        # Get query parameters
        limit = request.args.get('limit', default=100, type=int)
        event_type = request.args.get('event_type', default=None, type=str)
        app_id = request.args.get('app_id', default=None, type=str)
        status = request.args.get('status', default=None, type=str)
        start_date = request.args.get('start_date', default=None, type=str)
        end_date = request.args.get('end_date', default=None, type=str)
        
        # Validate limit
        if limit < 1 or limit > 1000:
            limit = 100
        
        history = storage.get_history(
            limit=limit,
            event_type=event_type,
            app_id=app_id,
            status=status,
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify({
            'history': history,
            'count': len(history)
        })
    except Exception as e:
        logger.error(f"Error getting history: {e}", exc_info=True)
        return jsonify({'error': 'Failed to get history'}), 500


@app.route('/api/settings', methods=['GET'])
@require_auth(storage)
def get_settings():
    """Get application settings"""
    try:
        settings = storage.get_settings()
        settings['version'] = APP_VERSION
        return jsonify(settings)
    except Exception as e:
        logger.error(f"Error getting settings: {e}", exc_info=True)
        return jsonify({'error': 'Failed to get settings'}), 500


@app.route('/api/settings', methods=['PUT'])
@require_auth(storage)
def update_settings():
    """Update application settings"""
    if not request.json:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    data = request.json
    
    # Validate settings
    if 'default_interval' in data:
        interval = data['default_interval']
        if interval:
            try:
                parse_interval(interval)
            except (ValueError, AttributeError):
                return jsonify({'error': 'Invalid interval format. Use format like: 6h, 30m, 1d'}), 400
    
    try:
        current_settings = storage.get_settings()
        # Merge with new settings
        current_settings.update(data)
        storage.save_settings(current_settings)
        
        # Reschedule jobs if interval changed
        if 'default_interval' in data:
            setup_scheduler()
        
        # Reload formatter and monitor with new settings
        global monitor, formatter
        formatter = DiscordFormatter(current_settings)
        monitor = AppStoreMonitor(storage, formatter, current_settings)
        
        # If auto_post_on_update setting changed, reschedule to ensure monitor has latest settings
        setup_scheduler()
        
        return jsonify(current_settings)
    except Exception as e:
        logger.error(f"Error updating settings: {e}", exc_info=True)
        return jsonify({'error': 'Failed to update settings'}), 500


# Initialize scheduler when module loads
# Wrap in try-except to handle errors gracefully
try:
    setup_scheduler()
except Exception as e:
    logger.error(f"Failed to initialize scheduler: {e}", exc_info=True)

# Reload monitor when settings change (helper function)
def reload_monitor():
    """Reload monitor with current settings"""
    global monitor, formatter
    current_settings = storage.get_settings()
    formatter = DiscordFormatter(current_settings)
    monitor = AppStoreMonitor(storage, formatter, current_settings)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8192))
    # Use production WSGI server in production (gunicorn recommended)
    # For self-hosted, Flask dev server is acceptable
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

