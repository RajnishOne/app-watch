import React, { useState, useEffect } from 'react';
import { ACCENT_PRESETS } from '../theme';
import { Icons } from '../components/Icons';
import {
  fetchAuthStatus,
  regenerateApiKeyRequest,
  fetchSettings,
  putSettings
} from '../api';
import { getHumanReadableError } from '../utils/errors';

export function SettingsPage({ onCancel, message, showMessage, section = 'general', onNavigateSection, theme, onThemeChange, accent, onAccentChange }) {
  const [settings, setSettings] = useState({
    default_interval: '12h',
    monitoring_enabled_by_default: true,
    auto_post_on_update: false,
    telegram_bot_token: '',
    smtp_host: '',
    smtp_port: '587',
    smtp_user: '',
    smtp_password: '',
    smtp_from: '',
    smtp_use_tls: true,
    version: '1.8.5',
    api_key: '',
    message_format_version_header: '# v{version}',
    message_format_section_header: '## {section}',
    message_format_bullet: '- ',
    message_format_empty_line_between_sections: true,
    message_format_no_release_notes: 'No release notes available.',
    message_format_include_version_header: true
  });
  const [apiKey, setApiKey] = useState('');
  const [regeneratingApiKey, setRegeneratingApiKey] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState({});

  const settingsSections = [
    { id: 'general', label: 'General' },
    { id: 'webhook', label: 'Webhook' },
    { id: 'message-format', label: 'Message Format' },
    { id: 'security', label: 'Security' },
    { id: 'appearance', label: 'Appearance' },
  ];

  useEffect(() => {
    loadSettings();
    loadApiKey();
    document.title = 'Settings - App Watch';
    return () => { document.title = 'App Watch'; };
  }, []);

  const loadApiKey = async () => {
    try {
      const data = await fetchAuthStatus();
      setApiKey(data.api_key || '');
    } catch (error) {
      console.error('Error loading API key:', error);
    }
  };

  const handleRegenerateApiKey = async () => {
    if (!window.confirm('Regenerate API key? This will invalidate the current key.')) return;

    try {
      setRegeneratingApiKey(true);
      const data = await regenerateApiKeyRequest();
      setApiKey(data.api_key);
      showMessage('API key regenerated successfully', 'success');
    } catch (error) {
      showMessage(getHumanReadableError(error.message || 'Failed to regenerate API key'), 'error');
    } finally {
      setRegeneratingApiKey(false);
    }
  };

  const loadSettings = async () => {
    try {
      setLoading(true);
      const data = await fetchSettings();
      setSettings(data);
    } catch (error) {
      showMessage(getHumanReadableError(error.message || 'Failed to load settings'), 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSettings(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
    if (errors[name]) {
      setErrors(prev => { const newErrors = { ...prev }; delete newErrors[name]; return newErrors; });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const newErrors = {};
    if (settings.default_interval && !/^\d+[hmsd]$/i.test(settings.default_interval.trim())) {
      newErrors.default_interval = 'Invalid interval format. Use: 6h, 30m, 1d';
    }
    
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      showMessage('Please fix the errors before saving', 'error');
      return;
    }

    try {
      setSaving(true);
      const { version, ...settingsToSave } = settings;
      await putSettings(settingsToSave);
      showMessage('Settings saved successfully');
    } catch (error) {
      showMessage(getHumanReadableError(error.message || 'Failed to save settings'), 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <>
        <div className="page-header">
          <div className="page-header-left">
            <h1 className="page-title">Settings</h1>
            <p className="page-subtitle">Configure application settings</p>
          </div>
        </div>
        <div className="page-content">
          <div className="loading">
            <div className="loading-spinner"></div>
            <span>Loading settings...</span>
          </div>
        </div>
      </>
    );
  }

  const renderSectionContent = () => {
    switch (section) {
      case 'general':
        return (
          <div className="settings-section">
            <div className="settings-section-header">
              <h3 className="settings-section-title">General Settings</h3>
              <p className="settings-section-description">Configure default behavior and monitoring preferences</p>
            </div>
            <div className="settings-section-body">
                <div className="form-group">
                  <label className="form-label">Default Check Interval</label>
                  <input
                    type="text"
                    name="default_interval"
                    value={settings.default_interval}
                    onChange={handleChange}
                    placeholder="12h"
                    className={`form-input ${errors.default_interval ? 'error' : ''}`}
                  />
                  <span className="form-hint">Default interval for checking updates (e.g., 6h, 30m, 1d)</span>
                  {errors.default_interval && <span className="form-error">{errors.default_interval}</span>}
                </div>

                <div className="form-group">
                  <div className="form-checkbox-group">
                    <input
                      type="checkbox"
                      id="monitoring_enabled_by_default"
                      name="monitoring_enabled_by_default"
                      checked={settings.monitoring_enabled_by_default}
                      onChange={handleChange}
                      className="form-checkbox"
                    />
                    <label htmlFor="monitoring_enabled_by_default" className="form-checkbox-label">
                      Enable Monitoring by Default
                    </label>
                  </div>
                  <span className="form-hint">New apps will have monitoring enabled automatically</span>
                </div>

                <div className="form-group">
                  <div className="form-checkbox-group">
                    <input
                      type="checkbox"
                      id="auto_post_on_update"
                      name="auto_post_on_update"
                      checked={settings.auto_post_on_update}
                      onChange={handleChange}
                      className="form-checkbox"
                    />
                    <label htmlFor="auto_post_on_update" className="form-checkbox-label">
                      Auto-Post Notifications on Update
                    </label>
                  </div>
                  <span className="form-hint">Automatically send notifications when a new version is detected</span>
                </div>
              </div>
            </div>
        );
      case 'webhook':
        return (
          <div className="settings-section">
            <div className="settings-section-header">
              <h3 className="settings-section-title">Webhook Settings</h3>
              <p className="settings-section-description">Default settings for notification destinations</p>
            </div>
            <div className="settings-section-body">
                <div className="form-group">
                  <label className="form-label">Telegram Bot Token</label>
                  <input
                    type="text"
                    name="telegram_bot_token"
                    value={settings.telegram_bot_token || ''}
                    onChange={handleChange}
                    placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
                    className="form-input"
                  />
                  <span className="form-hint">Default bot token for Telegram notifications</span>
                </div>

                <div className="form-group">
                  <label className="form-label">SMTP Host</label>
                  <input
                    type="text"
                    name="smtp_host"
                    value={settings.smtp_host || ''}
                    onChange={handleChange}
                    placeholder="smtp.gmail.com"
                    className="form-input"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">SMTP Port</label>
                  <input
                    type="text"
                    name="smtp_port"
                    value={settings.smtp_port || ''}
                    onChange={handleChange}
                    placeholder="587"
                    className="form-input"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">SMTP Username</label>
                  <input
                    type="text"
                    name="smtp_user"
                    value={settings.smtp_user || ''}
                    onChange={handleChange}
                    placeholder="your-email@example.com"
                    className="form-input"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">SMTP Password</label>
                  <input
                    type="password"
                    name="smtp_password"
                    value={settings.smtp_password || ''}
                    onChange={handleChange}
                    placeholder="Your SMTP password"
                    className="form-input"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">From Email Address</label>
                  <input
                    type="email"
                    name="smtp_from"
                    value={settings.smtp_from || ''}
                    onChange={handleChange}
                    placeholder="sender@example.com"
                    className="form-input"
                  />
                </div>

                <div className="form-group">
                  <div className="form-checkbox-group">
                    <input
                      type="checkbox"
                      id="smtp_use_tls"
                      name="smtp_use_tls"
                      checked={settings.smtp_use_tls !== false}
                      onChange={handleChange}
                      className="form-checkbox"
                    />
                    <label htmlFor="smtp_use_tls" className="form-checkbox-label">
                      Use TLS for SMTP
                    </label>
                  </div>
                </div>
              </div>
            </div>
        );
      case 'message-format':
        return (
          <div className="settings-section">
            <div className="settings-section-header">
              <h3 className="settings-section-title">Message Format Settings</h3>
              <p className="settings-section-description">Customize how release notes are formatted in webhook messages</p>
            </div>
            <div className="settings-section-body">
                <div className="form-group">
                  <div className="form-checkbox-group">
                    <input
                      type="checkbox"
                      id="message_format_include_version_header"
                      name="message_format_include_version_header"
                      checked={settings.message_format_include_version_header !== false}
                      onChange={handleChange}
                      className="form-checkbox"
                    />
                    <label htmlFor="message_format_include_version_header" className="form-checkbox-label">
                      Include Version Header
                    </label>
                  </div>
                  <span className="form-hint">Show version header at the top of messages</span>
                </div>

                <div className="form-group">
                  <label className="form-label">Version Header Format</label>
                  <input
                    type="text"
                    name="message_format_version_header"
                    value={settings.message_format_version_header || '# v{version}'}
                    onChange={handleChange}
                    placeholder="# v{version}"
                    className="form-input"
                  />
                  <span className="form-hint">Format for version header. Use {'{version}'} as placeholder. Examples: "# v{'{version}'}", "Version {'{version}'}", "**v{'{version}'}**"</span>
                </div>

                <div className="form-group">
                  <label className="form-label">Section Header Format</label>
                  <input
                    type="text"
                    name="message_format_section_header"
                    value={settings.message_format_section_header || '## {section}'}
                    onChange={handleChange}
                    placeholder="## {section}"
                    className="form-input"
                  />
                  <span className="form-hint">Format for section headers (New, Fixed, etc.). Use {`{section}`} as placeholder. Examples: "## {section}", "**{section}**", "{section}:"</span>
                </div>

                <div className="form-group">
                  <label className="form-label">Bullet Point Style</label>
                  <input
                    type="text"
                    name="message_format_bullet"
                    value={settings.message_format_bullet || '- '}
                    onChange={handleChange}
                    placeholder="- "
                    className="form-input"
                  />
                  <span className="form-hint">Bullet character(s) for list items. Examples: "- ", "* ", "• ", "→ "</span>
                </div>

                <div className="form-group">
                  <div className="form-checkbox-group">
                    <input
                      type="checkbox"
                      id="message_format_empty_line_between_sections"
                      name="message_format_empty_line_between_sections"
                      checked={settings.message_format_empty_line_between_sections !== false}
                      onChange={handleChange}
                      className="form-checkbox"
                    />
                    <label htmlFor="message_format_empty_line_between_sections" className="form-checkbox-label">
                      Empty Line Between Sections
                    </label>
                  </div>
                  <span className="form-hint">Add blank lines between different sections (New, Fixed, etc.)</span>
                </div>

                <div className="form-group">
                  <label className="form-label">No Release Notes Text</label>
                  <input
                    type="text"
                    name="message_format_no_release_notes"
                    value={settings.message_format_no_release_notes || 'No release notes available.'}
                    onChange={handleChange}
                    placeholder="No release notes available."
                    className="form-input"
                  />
                  <span className="form-hint">Text to display when release notes are empty</span>
                </div>
              </div>
            </div>
        );
      case 'security':
        return (
          <div className="settings-section">
            <div className="settings-section-header">
              <h3 className="settings-section-title">Security Settings</h3>
              <p className="settings-section-description">Manage API access for integrations</p>
            </div>
            <div className="settings-section-body">
                <div className="form-group">
                  <label className="form-label">API Key</label>
                  <div style={{ display: 'flex', gap: '12px' }}>
                    <input
                      type="text"
                      value={apiKey}
                      readOnly
                      className="form-input"
                      style={{ fontFamily: 'monospace', flex: 1 }}
                      onClick={(e) => e.target.select()}
                    />
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={handleRegenerateApiKey}
                      disabled={regeneratingApiKey}
                    >
                      {regeneratingApiKey ? 'Regenerating...' : 'Regenerate'}
                    </button>
                  </div>
                  <span className="form-hint">
                    Use this key for programmatic access via <code>X-Api-Key</code> header or Bearer token
                  </span>
                </div>
              </div>
            </div>
        );
      case 'appearance':
        return null; // Render separately outside form
      default:
        return null;
    }
  };

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Configure application settings</p>
        </div>
      </div>

      <div className="page-content">
        <div className="settings-layout">
          {/* Nested Settings Sidebar */}
          <aside className="settings-sidebar">
            <nav className="settings-nav">
              {settingsSections.map(sec => (
                <button
                  key={sec.id}
                  className={`settings-nav-item ${section === sec.id ? 'active' : ''}`}
                  onClick={() => onNavigateSection(sec.id)}
                >
                  {sec.label}
                </button>
              ))}
            </nav>
          </aside>

          {/* Settings Content */}
          <div className="settings-content-area">
            {section === 'appearance' ? (
              <div className="form-page">
                {message && (
                  <div className={`alert alert-${message.type}`}>
                    {message.text}
                  </div>
                )}

                <div className="settings-section">
                  <div className="settings-section-header">
                    <h3 className="settings-section-title">Appearance Settings</h3>
                    <p className="settings-section-description">Customize the look and feel of the application</p>
                  </div>
                  <div className="settings-section-body">
                    <div className="form-group">
                      <label className="form-label">Theme</label>
                      <select
                        value={theme}
                        onChange={(e) => onThemeChange(e.target.value)}
                        className="form-select"
                        style={{ maxWidth: '200px' }}
                      >
                        <option value="dark">Dark</option>
                        <option value="light">Light</option>
                      </select>
                      <span className="form-hint">Choose your preferred color theme</span>
                    </div>
                    <div className="form-group">
                      <label className="form-label">Accent color</label>
                      <div className="accent-swatches" style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '8px' }}>
                        {Object.entries(ACCENT_PRESETS).map(([key, { primary, label }]) => (
                          <button
                            key={key}
                            type="button"
                            className={`accent-swatch ${accent === key ? 'accent-swatch-active' : ''}`}
                            style={{
                              width: 40,
                              height: 40,
                              borderRadius: 8,
                              border: accent === key ? '3px solid var(--text-primary)' : '2px solid var(--border-color)',
                              background: primary,
                              cursor: 'pointer',
                              padding: 0,
                              flexShrink: 0,
                            }}
                            onClick={() => onAccentChange(key)}
                            title={label}
                            aria-label={`Accent ${label}`}
                          />
                        ))}
                      </div>
                      <span className="form-hint">Choose the accent color used for buttons and highlights</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="form-page">
                {message && (
                  <div className={`alert alert-${message.type}`}>
                    {message.text}
                  </div>
                )}

                <form onSubmit={handleSubmit}>
                  {renderSectionContent()}

                  <div className="form-actions">
                    <button type="submit" className="btn btn-primary btn-lg" disabled={saving}>
                      <Icons.Check /> {saving ? 'Saving...' : 'Save Settings'}
                    </button>
                  </div>
                </form>

                {section === 'general' && (
                  <div className="version-info">
                    <span className="version-label">Version</span>
                    <span className="version-value">{settings.version || '1.8.5'}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
