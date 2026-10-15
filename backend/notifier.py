"""
Multi-platform notification handler
Supports Discord, Slack, Telegram, Microsoft Teams, Email, and Generic webhooks
"""
import logging
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class NotificationHandler:
    """Handle notifications to multiple platforms"""
    
    def __init__(self, settings: Optional[Dict] = None):
        self.settings = settings or {}

    @staticmethod
    def _parse_telegram_chat_target(chat_target: str):
        """
        Parse a Telegram target in ``chat_id`` or ``chat_id_topic_id`` form.

        Telegram usernames may contain underscores, so the suffix notation is
        only interpreted for numeric chat IDs.
        """
        chat_target = str(chat_target or '').strip()
        if '_' not in chat_target:
            return chat_target, None, None

        chat_id, topic_id = chat_target.rsplit('_', 1)
        if not chat_id.lstrip('-').isdigit():
            return chat_target, None, None
        if not topic_id.isdigit() or int(topic_id) <= 0:
            return None, None, 'Telegram topic must use chat_id_topic_id format, for example -1001234567890_2'

        return chat_id, int(topic_id), None
    
    def send_notification(self, destination: Dict, app_name: str, version: str, release_notes: str, formatted_content: str) -> Tuple[bool, Optional[str]]:
        """
        Send notification to a destination
        
        Returns: (success: bool, error_message: Optional[str])
        """
        dest_type = destination.get('type', '').lower()
        
        try:
            if dest_type == 'discord':
                return self._send_discord(destination, formatted_content)
            elif dest_type == 'slack':
                return self._send_slack(destination, formatted_content)
            elif dest_type == 'telegram':
                return self._send_telegram(destination, app_name, version, release_notes, formatted_content)
            elif dest_type == 'teams':
                return self._send_teams(destination, app_name, version, release_notes, formatted_content)
            elif dest_type == 'email':
                return self._send_email(destination, app_name, version, release_notes, formatted_content)
            elif dest_type == 'generic':
                return self._send_generic(destination, app_name, version, release_notes, formatted_content)
            else:
                return False, f'Unknown notification type: {dest_type}'
        except Exception as e:
            logger.error(f"Error sending notification to {dest_type}: {e}", exc_info=True)
            return False, str(e)
    
    def _send_discord(self, destination: Dict, content: str) -> Tuple[bool, Optional[str]]:
        """Send notification to Discord webhook"""
        webhook_url = destination.get('webhook_url', '').strip()
        if not webhook_url:
            return False, 'Discord webhook URL is required'
        
        if not webhook_url.startswith('https://discord.com/api/webhooks/'):
            return False, 'Invalid Discord webhook URL'
        
        try:
            payload = {'content': content}
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True, None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error posting to Discord webhook: {e}")
            return False, f'Failed to post to Discord: {str(e)}'
    
    def _send_slack(self, destination: Dict, content: str) -> Tuple[bool, Optional[str]]:
        """Send notification to Slack webhook"""
        webhook_url = destination.get('webhook_url', '').strip()
        if not webhook_url:
            return False, 'Slack webhook URL is required'
        
        if not webhook_url.startswith('https://hooks.slack.com/'):
            return False, 'Invalid Slack webhook URL'
        
        try:
            # Convert markdown-like content to Slack format
            slack_text = self._convert_to_slack_format(content)
            payload = {'text': slack_text}
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True, None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error posting to Slack webhook: {e}")
            return False, f'Failed to post to Slack: {str(e)}'
    
    def _send_telegram(self, destination: Dict, app_name: str, version: str, release_notes: str, formatted_content: str) -> Tuple[bool, Optional[str]]:
        """Send notification to Telegram bot"""
        bot_token = destination.get('bot_token', '').strip()
        chat_target = destination.get('chat_id', '').strip()
        
        # Check if bot_token is in destination, otherwise use from settings
        if not bot_token:
            bot_token = self.settings.get('telegram_bot_token', '').strip()
        
        if not bot_token:
            return False, 'Telegram bot token is required (set in destination or settings)'
        
        if not chat_target:
            return False, 'Telegram chat ID is required'

        chat_id, message_thread_id, target_error = self._parse_telegram_chat_target(chat_target)
        if target_error:
            return False, target_error
        
        try:
            # Format message for Telegram
            telegram_text = self._convert_to_telegram_format(formatted_content)
            
            url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
            payload = {
                'chat_id': chat_id,
                'text': telegram_text,
                'parse_mode': 'Markdown'
            }
            if message_thread_id is not None:
                payload['message_thread_id'] = message_thread_id
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if not result.get('ok'):
                return False, f"Telegram API error: {result.get('description', 'Unknown error')}"
            
            return True, None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error posting to Telegram: {e}")
            return False, f'Failed to post to Telegram: {str(e)}'
    
    def _send_teams(self, destination: Dict, app_name: str, version: str, release_notes: str, formatted_content: str) -> Tuple[bool, Optional[str]]:
        """Send notification to Microsoft Teams webhook"""
        webhook_url = destination.get('webhook_url', '').strip()
        if not webhook_url:
            return False, 'Microsoft Teams webhook URL is required'
        
        if not webhook_url.startswith('https://'):
            return False, 'Microsoft Teams webhook URL must use HTTPS'
        
        try:
            # Format as Teams message card
            teams_text = self._convert_to_teams_format(app_name, version, release_notes, formatted_content)
            
            payload = {
                '@type': 'MessageCard',
                '@context': 'https://schema.org/extensions',
                'summary': f'{app_name} v{version}',
                'themeColor': '0078D4',
                'title': f'{app_name} v{version}',
                'text': teams_text
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True, None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error posting to Teams webhook: {e}")
            return False, f'Failed to post to Teams: {str(e)}'
    
    def _send_email(self, destination: Dict, app_name: str, version: str, release_notes: str, formatted_content: str) -> Tuple[bool, Optional[str]]:
        """Send notification via email (SMTP)"""
        to_email = destination.get('email', '').strip()
        if not to_email:
            return False, 'Email address is required'
        
        # Get SMTP settings from destination or global settings
        smtp_host = destination.get('smtp_host', '').strip() or self.settings.get('smtp_host', '').strip()
        smtp_port = destination.get('smtp_port', '') or self.settings.get('smtp_port', '587')
        smtp_user = destination.get('smtp_user', '').strip() or self.settings.get('smtp_user', '').strip()
        smtp_password = destination.get('smtp_password', '').strip() or self.settings.get('smtp_password', '').strip()
        smtp_from = destination.get('smtp_from', '').strip() or self.settings.get('smtp_from', '').strip() or smtp_user
        smtp_use_tls = destination.get('smtp_use_tls', True) if 'smtp_use_tls' in destination else self.settings.get('smtp_use_tls', True)
        
        if not smtp_host:
            return False, 'SMTP host is required (set in destination or settings)'
        
        try:
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'{app_name} v{version} - New Release'
            msg['From'] = smtp_from
            msg['To'] = to_email
            
            # Convert formatted content to HTML
            html_content = self._convert_to_html_format(formatted_content)
            
            # Add both plain text and HTML versions
            text_part = MIMEText(formatted_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            smtp = smtplib.SMTP(smtp_host, int(smtp_port))
            if smtp_use_tls:
                smtp.starttls()
            
            if smtp_user and smtp_password:
                smtp.login(smtp_user, smtp_password)
            
            smtp.send_message(msg)
            smtp.quit()
            
            return True, None
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False, f'Failed to send email: {str(e)}'
    
    def _send_generic(self, destination: Dict, app_name: str, version: str, release_notes: str, formatted_content: str) -> Tuple[bool, Optional[str]]:
        """Send notification to generic webhook (HTTP POST)"""
        webhook_url = destination.get('webhook_url', '').strip()
        if not webhook_url:
            return False, 'Generic webhook URL is required'
        
        if not webhook_url.startswith('http://') and not webhook_url.startswith('https://'):
            return False, 'Invalid webhook URL (must start with http:// or https://)'
        
        try:
            # Get custom payload template or use default
            payload_template = destination.get('payload_template', '').strip()
            headers = destination.get('headers', {})
            
            if payload_template:
                # Use custom payload template
                # Replace placeholders
                payload_str = payload_template.replace('{{app_name}}', app_name)
                payload_str = payload_str.replace('{{version}}', version)
                payload_str = payload_str.replace('{{release_notes}}', release_notes)
                payload_str = payload_str.replace('{{formatted_content}}', formatted_content)
                
                import json
                try:
                    payload = json.loads(payload_str)
                except json.JSONDecodeError:
                    return False, 'Invalid JSON in payload template'
            else:
                # Default payload
                payload = {
                    'app_name': app_name,
                    'version': version,
                    'release_notes': release_notes,
                    'formatted_content': formatted_content
                }
            
            # Set default headers if not provided
            if not headers:
                headers = {'Content-Type': 'application/json'}
            
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return True, None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error posting to generic webhook: {e}")
            return False, f'Failed to post to webhook: {str(e)}'
    
    def _convert_to_slack_format(self, content: str) -> str:
        """Convert markdown content to Slack format"""
        # Slack uses *bold* and _italic_, and `code`
        # Convert # headers to *bold*
        text = content
        text = text.replace('# ', '*')
        text = text.replace('## ', '*')
        return text
    
    def _convert_to_telegram_format(self, content: str) -> str:
        """Convert content to Telegram Markdown format"""
        # Telegram supports Markdown, but has some limitations
        # Escape special characters that might break formatting
        text = content
        # Telegram uses *bold*, _italic_, `code`, and ```code blocks```
        return text
    
    def _convert_to_teams_format(self, app_name: str, version: str, release_notes: str, formatted_content: str) -> str:
        """Convert content to Microsoft Teams format"""
        # Teams uses plain text in message cards
        # Remove markdown formatting for cleaner display
        text = formatted_content
        text = text.replace('# ', '')
        text = text.replace('## ', '')
        text = text.replace('**', '')
        text = text.replace('*', '')
        return text
    
    def _convert_to_html_format(self, content: str) -> str:
        """Convert markdown content to HTML"""
        import re
        html = content
        
        # Convert headers
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        
        # Split into lines for processing
        lines = html.split('\n')
        result_lines = []
        in_list = False
        
        for line in lines:
            line = line.strip()
            if not line:
                if in_list:
                    result_lines.append('</ul>')
                    in_list = False
                result_lines.append('<br>')
            elif line.startswith('- '):
                if not in_list:
                    result_lines.append('<ul>')
                    in_list = True
                result_lines.append(f'<li>{line[2:]}</li>')
            else:
                if in_list:
                    result_lines.append('</ul>')
                    in_list = False
                # Escape HTML special characters
                line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                result_lines.append(f'<p>{line}</p>')
        
        if in_list:
            result_lines.append('</ul>')
        
        html_content = '\n'.join(result_lines)
        return f'<html><body>{html_content}</body></html>'

