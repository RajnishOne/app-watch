"""
App Store API integration
"""
import contextlib
import logging
import os
import requests
import time
from datetime import datetime
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from backend.notifier import NotificationHandler

try:
    from google_play_scraper import app as play_app
except ImportError:
    play_app = None

try:
    import fcntl
except ImportError:
    fcntl = None

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def file_lock(lock_path):
    """Cross-process file lock using fcntl (Unix) with no-op fallback for Windows."""
    if fcntl is None:
        yield
        return

    lock_file = None
    try:
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        lock_file = open(lock_path, 'w')
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        yield
    finally:
        if lock_file:
            try:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
            except IOError:
                pass
            lock_file.close()


class AppStoreMonitor:
    """Monitor App Store apps for new releases"""
    
    ITUNES_LOOKUP_URL = "https://itunes.apple.com/lookup"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    
    def __init__(self, storage, formatter, settings=None):
        self.storage = storage
        self.formatter = formatter
        self.settings = settings or {}
        self.notifier = NotificationHandler(settings)
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=self.RETRY_DELAY,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
    
    def _normalize_country(self, country):
        """Normalize App Store country code; default to US when invalid/missing."""
        code = str(country or "us").strip().lower()
        if len(code) != 2 or not code.isalpha():
            return "us"
        return code

    def fetch_app_info(self, app_store_id, country="us"):
        """Fetch app information from iTunes Lookup API with retry logic"""
        country_code = self._normalize_country(country)
        params = {
            'id': app_store_id,
            'country': country_code
        }
        
        last_exception = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = self.session.get(
                    self.ITUNES_LOOKUP_URL, 
                    params=params, 
                    timeout=10
                )
                response.raise_for_status()
                
                data = response.json()
                
                if data.get('resultCount', 0) == 0:
                    return None
                
                app_info = data['results'][0]
                
                # Get artwork URL - prefer higher resolution, fallback to lower
                artwork_url = (
                    app_info.get('artworkUrl512') or 
                    app_info.get('artworkUrl100') or 
                    app_info.get('artworkUrl60') or
                    None
                )
                
                return {
                    'version': app_info.get('version'),
                    'releaseNotes': app_info.get('releaseNotes', ''),
                    'bundleId': app_info.get('bundleId'),
                    'trackName': app_info.get('trackName'),
                    'artistName': app_info.get('artistName'),
                    'artworkUrl': artwork_url
                }
            except (requests.exceptions.ConnectionError, 
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException) as e:
                last_exception = e
                if attempt < self.MAX_RETRIES:
                    wait_time = self.RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.MAX_RETRIES + 1} failed for app {app_store_id} ({country_code}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {self.MAX_RETRIES + 1} attempts failed for app {app_store_id} ({country_code}): {e}")
            except Exception as e:
                logger.error(f"Unexpected error fetching app info for {app_store_id} ({country_code}): {e}", exc_info=True)
                raise
        
        # If we exhausted all retries, raise the last exception
        if last_exception:
            raise last_exception
            
    def fetch_android_app_info(self, package_id, country="us"):
        """Fetch app information from Google Play Store scraper with retry logic"""
        country_code = self._normalize_country(country)
        
        last_exception = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                if play_app is None:
                    raise ImportError("google-play-scraper is not installed or failed to import")
                    
                result = play_app(
                    package_id,
                    lang='en',
                    country=country_code
                )
                
                if not result:
                    return None
                
                return {
                    'version': result.get('version'),
                    'releaseNotes': result.get('recentChanges', ''),
                    'bundleId': package_id,
                    'trackName': result.get('title'),
                    'artistName': result.get('developer'),
                    'artworkUrl': result.get('icon'),
                    'updated': result.get('updated')  # Unix timestamp in ms
                }
            except Exception as e:
                last_exception = e
                if attempt < self.MAX_RETRIES:
                    wait_time = self.RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.MAX_RETRIES + 1} failed for Android app {package_id} ({country_code}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {self.MAX_RETRIES + 1} attempts failed for Android app {package_id} ({country_code}): {e}")
        
        if last_exception:
            raise last_exception
    
    def check_app(self, app):
        """Check app for new version and post if needed"""
        app_id = app['id']
        app_store_id = app['app_store_id']
        app_store_country = self._normalize_country(app.get('app_store_country', 'us'))
        platform = app.get('platform', 'ios')
        
        # Get notification destinations - support both new format and legacy webhook_url
        notification_destinations = app.get('notification_destinations', [])
        if not notification_destinations and app.get('webhook_url'):
            # Legacy support - convert old webhook_url to new format
            notification_destinations = [{
                'type': 'discord',
                'webhook_url': app['webhook_url']
            }]
        
        lock_path = self.storage.data_dir / 'apps' / app_id / 'check.lock'
        
        try:
            with file_lock(lock_path):
                # Check if another process/thread checked this app recently (within past 10 seconds)
                last_check_str = self.storage.get_last_check(app_id)
                if last_check_str:
                    try:
                        last_check_time = datetime.fromisoformat(last_check_str)
                        if (datetime.now() - last_check_time).total_seconds() < 10:
                            current_version = self.storage.get_current_version(app_id)
                            last_version = self.storage.get_last_version(app_id)
                            logger.info(f"App {app_id} was checked recently ({(datetime.now() - last_check_time).total_seconds():.1f}s ago). Skipping duplicate check.")
                            return {
                                'success': True,
                                'message': 'Checked recently (cached)',
                                'current_version': current_version,
                                'last_version': last_version,
                                'checked_at': last_check_str,
                                'formatted_preview': self.formatter.format_release_notes(current_version or '', '')
                            }
                    except Exception as e:
                        logger.debug(f"Error parsing last check time: {e}")

                # Fetch current app info
                if platform == 'android':
                    app_info = self.fetch_android_app_info(app_store_id, app_store_country)
                else:
                    app_info = self.fetch_app_info(app_store_id, app_store_country)
                
                if not app_info:
                    store_name = 'Google Play' if platform == 'android' else 'App Store'
                    return {
                        'success': False,
                        'error': f'App not found in {store_name}',
                        'checked_at': datetime.now().isoformat()
                    }
                
                current_version = app_info['version']
                release_notes = app_info.get('releaseNotes', '')
                
                # Get last posted version and other track states
                last_version = self.storage.get_last_version(app_id)
                last_updated_time = self.storage.get_last_updated_time(app_id) if platform == 'android' else None
                
                # Update last check time and current version
                self.storage.update_last_check(app_id, datetime.now().isoformat())
                self.storage.save_current_version(app_id, current_version)
                
                # For Android, also save the updated timestamp
                if platform == 'android' and app_info.get('updated'):
                    self.storage.save_last_updated_time(app_id, app_info['updated'])
                
                # Update app icon URL if available
                artwork_url = app_info.get('artworkUrl')
                if artwork_url:
                    # Update icon URL in app data
                    app_data = self.storage.get_app(app_id)
                    if app_data:
                        app_data['icon_url'] = artwork_url
                        self.storage.save_app(app_data)
                
                # Determine if version has changed / updated
                is_updated = False
                if not last_version:
                    is_updated = True
                elif platform == 'android':
                    current_updated_time = app_info.get('updated')
                    if current_updated_time and last_updated_time:
                        if str(current_updated_time) != str(last_updated_time):
                            is_updated = True
                    elif current_version != last_version:
                        is_updated = True
                else:
                    if current_version != last_version:
                        is_updated = True

                # Check if version changed
                if not is_updated:
                    return {
                        'success': True,
                        'message': 'No new version',
                        'current_version': current_version,
                        'last_version': last_version,
                        'checked_at': datetime.now().isoformat(),
                        'formatted_preview': self.formatter.format_release_notes(current_version, release_notes)
                    }
                
                # New version detected - check if auto-post is enabled
                auto_post_enabled = self.settings.get('auto_post_on_update', False)
                
                if not auto_post_enabled:
                    # Auto-post is disabled, just return the new version info without posting
                    logger.info(f"New version {current_version} detected for app {app_id}, but auto-post is disabled")
                    return {
                        'success': True,
                        'message': 'New version detected (auto-post disabled)',
                        'current_version': current_version,
                        'last_version': last_version,
                        'checked_at': datetime.now().isoformat(),
                        'formatted_preview': self.formatter.format_release_notes(current_version, release_notes),
                        'auto_post_disabled': True
                    }
                
                # Auto-post is enabled - post to all configured destinations
                formatted_notes = self.formatter.format_release_notes(current_version, release_notes)
                app_name = app.get('name', 'App')
                
                # Post to all notification destinations
                success_count = 0
                error_messages = []
                destination_results = []
                
                for dest in notification_destinations:
                    dest_type = dest.get('type', 'unknown')
                    success, error_msg = self.notifier.send_notification(
                        dest, app_name, current_version, release_notes, formatted_notes
                    )
                    if success:
                        success_count += 1
                        destination_results.append({'type': dest_type, 'status': 'success'})
                    else:
                        error_messages.append(f'{dest_type}: {error_msg or "Failed"}')
                        destination_results.append({'type': dest_type, 'status': 'error', 'error': error_msg})
                
                if success_count > 0:
                    # Update last posted version if at least one destination succeeded
                    self.storage.save_last_version(app_id, current_version)
                    message = f'New version posted to {success_count} destination(s)'
                    if error_messages:
                        message += f' ({len(error_messages)} failed)'
                    
                    # Log successful post
                    self.storage.add_history_entry(
                        event_type='post',
                        app_id=app_id,
                        app_name=app_name,
                        status='success',
                        message=f'New version {current_version} posted to {success_count} destination(s)',
                        details={
                            'version': current_version,
                            'previous_version': last_version,
                            'success_count': success_count,
                            'failed_count': len(error_messages),
                            'destinations': destination_results
                        }
                    )
                    
                    return {
                        'success': True,
                        'message': message,
                        'current_version': current_version,
                        'last_version': last_version,
                        'checked_at': datetime.now().isoformat(),
                        'formatted_preview': formatted_notes
                    }
                else:
                    error_msg = 'Failed to post to any notification destination'
                    if error_messages:
                        error_msg = '; '.join(error_messages)
                    
                    # Log failed post
                    self.storage.add_history_entry(
                        event_type='post',
                        app_id=app_id,
                        app_name=app_name,
                        status='error',
                        message=f'Failed to post version {current_version}',
                        details={
                            'version': current_version,
                            'error': error_msg,
                            'destinations': destination_results
                        }
                    )
                    
                    return {
                        'success': False,
                        'error': error_msg,
                        'current_version': current_version,
                        'checked_at': datetime.now().isoformat(),
                        'formatted_preview': formatted_notes
                    }
        
        except Exception as e:
            logger.error(f"Error checking app {app_id}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'checked_at': datetime.now().isoformat()
            }
    
    def post_to_discord(self, app):
        """Manually post current release notes to all configured notification destinations"""
        app_id = app['id']
        app_store_id = app['app_store_id']
        app_store_country = self._normalize_country(app.get('app_store_country', 'us'))
        platform = app.get('platform', 'ios')
        
        # Get notification destinations - support both new format and legacy webhook_url
        notification_destinations = app.get('notification_destinations', [])
        if not notification_destinations and app.get('webhook_url'):
            # Legacy support - convert old webhook_url to new format
            notification_destinations = [{
                'type': 'discord',
                'webhook_url': app['webhook_url']
            }]
        
        try:
            # Fetch current app info
            if platform == 'android':
                app_info = self.fetch_android_app_info(app_store_id, app_store_country)
            else:
                app_info = self.fetch_app_info(app_store_id, app_store_country)
            
            if not app_info:
                store_name = 'Google Play' if platform == 'android' else 'App Store'
                return {
                    'success': False,
                    'error': f'App not found in {store_name}'
                }
            
            current_version = app_info['version']
            release_notes = app_info.get('releaseNotes', '')
            
            # Update current version
            self.storage.save_current_version(app_id, current_version)
            
            # For Android, also save the updated timestamp
            if platform == 'android' and app_info.get('updated'):
                self.storage.save_last_updated_time(app_id, app_info['updated'])
            
            # Format and post to all destinations
            formatted_notes = self.formatter.format_release_notes(current_version, release_notes)
            app_name = app.get('name', 'App')
            
            success_count = 0
            error_messages = []
            destination_results = []
            
            for dest in notification_destinations:
                dest_type = dest.get('type', 'unknown')
                success, error_msg = self.notifier.send_notification(
                    dest, app_name, current_version, release_notes, formatted_notes
                )
                if success:
                    success_count += 1
                    destination_results.append({'type': dest_type, 'status': 'success'})
                else:
                    error_messages.append(f'{dest_type}: {error_msg or "Failed"}')
                    destination_results.append({'type': dest_type, 'status': 'error', 'error': error_msg})
            
            if success_count > 0:
                # Update last posted version if at least one destination succeeded
                self.storage.save_last_version(app_id, current_version)
                message = f'Posted to {success_count} destination(s)'
                if error_messages:
                    message += f' ({len(error_messages)} failed)'
                
                # Log successful manual post
                self.storage.add_history_entry(
                    event_type='post',
                    app_id=app_id,
                    app_name=app_name,
                    status='success',
                    message=f'Manually posted version {current_version} to {success_count} destination(s)',
                    details={
                        'version': current_version,
                        'success_count': success_count,
                        'failed_count': len(error_messages),
                        'destinations': destination_results,
                        'manual': True
                    }
                )
                
                return {
                    'success': True,
                    'message': message,
                    'version': current_version,
                    'formatted_preview': formatted_notes
                }
            else:
                error_msg = 'Failed to post to any notification destination'
                if error_messages:
                    error_msg = '; '.join(error_messages)
                
                # Log failed manual post
                self.storage.add_history_entry(
                    event_type='post',
                    app_id=app_id,
                    app_name=app_name,
                    status='error',
                    message=f'Failed to manually post version {current_version}',
                    details={
                        'version': current_version,
                        'error': error_msg,
                        'destinations': destination_results,
                        'manual': True
                    }
                )
                
                return {
                    'success': False,
                    'error': error_msg,
                    'version': current_version,
                    'formatted_preview': formatted_notes
                }
        
        except Exception as e:
            logger.error(f"Error posting to notification destinations for app {app_id}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    

