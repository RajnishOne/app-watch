"""
Storage management for app data and version tracking
"""
import json
import logging
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class StorageManager:
    """Manage app data and version storage"""
    
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.apps_file = self.data_dir / 'apps.json'
        self.settings_file = self.data_dir / 'settings.json'
        self.auth_file = self.data_dir / 'auth.json'
        self.history_file = self.data_dir / 'history.json'
        self._ensure_apps_file()
        self._ensure_settings_file()
        self._ensure_auth_file()
        self._strip_user_authentication()
        self._ensure_history_file()
    
    def _ensure_apps_file(self):
        """Ensure apps.json exists"""
        if not self.apps_file.exists():
            self._save_apps({})
    
    def _ensure_settings_file(self):
        """Ensure settings.json exists"""
        if not self.settings_file.exists():
            default_settings = {
                'default_interval': '12h',
                'monitoring_enabled_by_default': True,
                'auto_post_on_update': False,
                'telegram_bot_token': '',
                'smtp_host': '',
                'smtp_port': '587',
                'smtp_user': '',
                'smtp_password': '',
                'smtp_from': '',
                'smtp_use_tls': True,
                'message_format_version_header': '# v{version}',
                'message_format_section_header': '## {section}',
                'message_format_bullet': '- ',
                'message_format_empty_line_between_sections': True,
                'message_format_no_release_notes': 'No release notes available.',
                'message_format_include_version_header': True
            }
            self._save_settings(default_settings)
    
    def _ensure_auth_file(self):
        """Ensure auth.json exists"""
        if not self.auth_file.exists():
            default_auth = {
                'enabled': False,
                'auth_type': 'forms',  # 'basic' or 'forms'
                'username': '',
                'password_hash': '',
                'bypass_local_networks': False,
                'api_key': self._generate_api_key()
            }
            self._save_auth(default_auth)

    def _strip_user_authentication(self):
        """Remove stored login credentials and disable password prompts."""
        auth = self.get_auth()
        if auth.get('enabled') or auth.get('username') or auth.get('password_hash'):
            auth['enabled'] = False
            auth['username'] = ''
            auth['password_hash'] = ''
            self._save_auth(auth)
            logger.info('User authentication disabled; login credentials cleared from storage.')

    def _ensure_history_file(self):
        """Ensure history.json exists"""
        if not self.history_file.exists():
            self._save_history([])
    
    def _load_settings(self):
        """Load settings from JSON file"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return {}
    
    def _save_settings(self, settings_dict):
        """Save settings to JSON file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings_dict, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            raise
    
    def get_settings(self):
        """Get all settings with defaults"""
        settings = self._load_settings()
        # Ensure defaults are always present
        defaults = {
            'default_interval': '12h',
            'monitoring_enabled_by_default': True,
            'auto_post_on_update': False,
            'telegram_bot_token': '',
            'smtp_host': '',
            'smtp_port': '587',
            'smtp_user': '',
            'smtp_password': '',
            'smtp_from': '',
            'smtp_use_tls': True,
            'message_format_version_header': '# v{version}',
            'message_format_section_header': '## {section}',
            'message_format_bullet': '- ',
            'message_format_empty_line_between_sections': True,
            'message_format_no_release_notes': 'No release notes available.',
            'message_format_include_version_header': True
        }
        # Merge defaults with loaded settings (loaded settings take precedence)
        return {**defaults, **settings}
    
    def save_settings(self, settings_data):
        """Save settings"""
        self._save_settings(settings_data)
        return True
    
    def _load_apps(self):
        """Load apps from JSON file"""
        try:
            if self.apps_file.exists():
                with open(self.apps_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading apps: {e}")
            return {}
    
    def _save_apps(self, apps_dict):
        """Save apps to JSON file"""
        try:
            with open(self.apps_file, 'w') as f:
                json.dump(apps_dict, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving apps: {e}")
            raise
    
    def get_all_apps(self):
        """Get all apps as a list"""
        apps_dict = self._load_apps()
        apps = []
        
        for app_id, app_data in apps_dict.items():
            app = {
                'id': app_id,
                **app_data
            }
            
            # Add status information
            app['current_version'] = self.get_current_version(app_id)
            app['last_posted_version'] = self.get_last_version(app_id)
            app['last_check'] = self.get_last_check(app_id)
            
            apps.append(app)
        
        return apps
    
    def get_app(self, app_id):
        """Get a specific app"""
        apps_dict = self._load_apps()
        
        if app_id not in apps_dict:
            return None
        
        app_data = apps_dict[app_id]
        app = {
            'id': app_id,
            **app_data
        }
        
        # Add status information
        app['current_version'] = self.get_current_version(app_id)
        app['last_posted_version'] = self.get_last_version(app_id)
        app['last_check'] = self.get_last_check(app_id)
        
        return app
    
    def save_app(self, app_data):
        """Save or update an app"""
        apps_dict = self._load_apps()
        
        # Generate ID if new
        if 'id' not in app_data or app_data['id'] not in apps_dict:
            app_id = str(uuid.uuid4())
        else:
            app_id = app_data['id']
        
        # Remove status fields before saving
        save_data = {
            'name': app_data['name'],
            'app_store_id': app_data['app_store_id'],
            'interval_override': app_data.get('interval_override'),
            'enabled': app_data.get('enabled', True)
        }
        
        # Save icon URL if provided
        if 'icon_url' in app_data:
            save_data['icon_url'] = app_data['icon_url']
        
        # Handle notification destinations - support both new format and legacy webhook_url
        if 'notification_destinations' in app_data and app_data['notification_destinations']:
            save_data['notification_destinations'] = app_data['notification_destinations']
        elif 'webhook_url' in app_data and app_data['webhook_url']:
            # Legacy support - convert old webhook_url to new format
            save_data['notification_destinations'] = [{
                'type': 'discord',
                'webhook_url': app_data['webhook_url']
            }]
        else:
            save_data['notification_destinations'] = []
        
        apps_dict[app_id] = save_data
        self._save_apps(apps_dict)
        
        return app_id
    
    def delete_app(self, app_id):
        """Delete an app"""
        apps_dict = self._load_apps()
        
        if app_id not in apps_dict:
            return False
        
        del apps_dict[app_id]
        self._save_apps(apps_dict)
        
        # Also delete version files
        version_file = self._get_version_file(app_id)
        if version_file.exists():
            version_file.unlink()
        
        current_version_file = self._get_current_version_file(app_id)
        if current_version_file.exists():
            current_version_file.unlink()
        
        # Delete check time file
        check_file = self._get_check_file(app_id)
        if check_file.exists():
            check_file.unlink()
        
        return True
    
    def _get_version_file(self, app_id):
        """Get path to version file for an app"""
        app_dir = self.data_dir / 'apps' / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir / 'version.txt'
    
    def _get_check_file(self, app_id):
        """Get path to last check time file"""
        app_dir = self.data_dir / 'apps' / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir / 'check.txt'
    
    def _get_current_version_file(self, app_id):
        """Get path to current version file (last checked version from App Store)"""
        app_dir = self.data_dir / 'apps' / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir / 'current_version.txt'
    
    def get_last_version(self, app_id):
        """Get last posted version for an app"""
        version_file = self._get_version_file(app_id)
        
        if version_file.exists():
            try:
                return version_file.read_text().strip()
            except Exception as e:
                logger.error(f"Error reading version file: {e}")
                return None
        
        return None
    
    def save_last_version(self, app_id, version):
        """Save last posted version for an app"""
        version_file = self._get_version_file(app_id)
        
        try:
            version_file.write_text(version)
        except Exception as e:
            logger.error(f"Error saving version: {e}")
            raise
    
    def get_last_check(self, app_id):
        """Get last check time for an app"""
        check_file = self._get_check_file(app_id)
        
        if check_file.exists():
            try:
                return check_file.read_text().strip()
            except Exception as e:
                logger.error(f"Error reading check file: {e}")
                return None
        
        return None
    
    def update_last_check(self, app_id, timestamp):
        """Update last check time for an app"""
        check_file = self._get_check_file(app_id)
        
        try:
            check_file.write_text(timestamp)
        except Exception as e:
            logger.error(f"Error saving check time: {e}")
    
    def get_current_version(self, app_id):
        """Get current version (last checked from App Store)"""
        version_file = self._get_current_version_file(app_id)
        
        if version_file.exists():
            try:
                return version_file.read_text().strip()
            except Exception as e:
                logger.error(f"Error reading current version file: {e}")
                return None
        
        return None
    
    def save_current_version(self, app_id, version):
        """Save current version (from App Store check)"""
        version_file = self._get_current_version_file(app_id)
        
        try:
            version_file.write_text(version)
        except Exception as e:
            logger.error(f"Error saving current version: {e}")
            raise
    
    # Authentication methods
    def _load_auth(self):
        """Load authentication settings from JSON file"""
        try:
            if self.auth_file.exists():
                with open(self.auth_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading auth: {e}")
            return {}
    
    def _save_auth(self, auth_dict):
        """Save authentication settings to JSON file"""
        try:
            with open(self.auth_file, 'w') as f:
                json.dump(auth_dict, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving auth: {e}")
            raise
    
    def get_auth(self):
        """Get authentication settings"""
        auth = self._load_auth()
        defaults = {
            'enabled': False,
            'auth_type': 'forms',
            'username': '',
            'password_hash': '',
            'bypass_local_networks': False,
            'api_key': self._generate_api_key() if not auth.get('api_key') else auth.get('api_key')
        }
        result = {**defaults, **auth}
        # Ensure API key exists
        if not result.get('api_key'):
            result['api_key'] = self._generate_api_key()
            self._save_auth(result)
        return result
    
    def save_auth(self, auth_data):
        """Save authentication settings"""
        # Hash password if provided
        if 'password' in auth_data and auth_data['password']:
            auth_data['password_hash'] = self._hash_password(auth_data['password'])
            del auth_data['password']
        # Don't save password_hash if it's empty
        if 'password_hash' in auth_data and not auth_data['password_hash']:
            del auth_data['password_hash']
        
        self._save_auth(auth_data)
        return True
    
    def _hash_password(self, password):
        """Hash a password using SHA256"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def verify_password(self, password):
        """Verify a password against stored hash"""
        auth = self.get_auth()
        if not auth.get('password_hash'):
            return False
        password_hash = self._hash_password(password)
        return password_hash == auth.get('password_hash')
    
    def is_auth_enabled(self):
        """Check if authentication is enabled"""
        auth = self.get_auth()
        return auth.get('enabled', False)
    
    def is_auth_configured(self):
        """Check if authentication is configured (has username and password)"""
        auth = self.get_auth()
        return bool(auth.get('username') and auth.get('password_hash'))
    
    def _generate_api_key(self):
        """Generate a secure random API key"""
        return secrets.token_urlsafe(32)
    
    def regenerate_api_key(self):
        """Regenerate the API key"""
        auth = self.get_auth()
        auth['api_key'] = self._generate_api_key()
        self._save_auth(auth)
        return auth['api_key']
    
    def verify_api_key(self, api_key):
        """Verify an API key"""
        auth = self.get_auth()
        stored_key = auth.get('api_key', '')
        return bool(stored_key and api_key == stored_key)
    
    # History/Activity log methods
    def _load_history(self):
        """Load history from JSON file"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return []
    
    def _save_history(self, history_list):
        """Save history to JSON file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(history_list, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving history: {e}")
            raise
    
    def add_history_entry(self, event_type, app_id=None, app_name=None, status='info', message='', details=None):
        """
        Add an entry to the activity history
        
        Args:
            event_type: Type of event (check, post, app_created, app_updated, etc.)
            app_id: ID of the app (if applicable)
            app_name: Name of the app (if applicable)
            status: Status of the event ('success', 'error', 'warning', 'info')
            message: Human-readable message
            details: Additional details (dict)
        """
        entry = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'app_id': app_id,
            'app_name': app_name,
            'status': status,
            'message': message,
            'details': details or {}
        }
        
        history = self._load_history()
        history.insert(0, entry)  # Add to beginning (newest first)
        
        # Limit history to last 1000 entries to prevent file from growing too large
        MAX_HISTORY_ENTRIES = 1000
        if len(history) > MAX_HISTORY_ENTRIES:
            history = history[:MAX_HISTORY_ENTRIES]
        
        self._save_history(history)
        return entry
    
    def get_history(self, limit=100, event_type=None, app_id=None, status=None, start_date=None, end_date=None):
        """
        Get activity history with optional filtering
        
        Args:
            limit: Maximum number of entries to return
            event_type: Filter by event type
            app_id: Filter by app ID
            status: Filter by status (success, error, warning, info)
            start_date: Filter entries after this date (ISO format)
            end_date: Filter entries before this date (ISO format)
        
        Returns:
            List of history entries
        """
        history = self._load_history()
        
        # Apply filters
        filtered = []
        for entry in history:
            # Event type filter
            if event_type and entry.get('event_type') != event_type:
                continue
            
            # App ID filter
            if app_id and entry.get('app_id') != app_id:
                continue
            
            # Status filter
            if status and entry.get('status') != status:
                continue
            
            # Date filters
            if start_date:
                if entry.get('timestamp', '') < start_date:
                    continue
            if end_date:
                if entry.get('timestamp', '') > end_date:
                    continue
            
            filtered.append(entry)
        
        # Apply limit
        return filtered[:limit]
    
    def clear_history(self, older_than_days=None):
        """
        Clear history entries
        
        Args:
            older_than_days: If provided, only clear entries older than this many days
        """
        if older_than_days:
            from datetime import timedelta
            cutoff_date = (datetime.now() - timedelta(days=older_than_days)).isoformat()
            history = self._load_history()
            filtered = [e for e in history if e.get('timestamp', '') >= cutoff_date]
            self._save_history(filtered)
        else:
            self._save_history([])

