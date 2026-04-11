import React, { useState, useEffect } from 'react';
import { Icons } from '../components/Icons';
import { fetchSettings, fetchAppMetadata } from '../api';

// Helper function to get webhook type instructions
const getWebhookInstructions = (type) => {
  const instructions = {
    discord: 'Go to Discord Server Settings → Integrations → Webhooks → New Webhook. Copy the webhook URL.',
    slack: 'Go to Slack App Settings → Incoming Webhooks → Add New Webhook. Copy the webhook URL.',
    telegram: 'Message @BotFather to create a bot and get a token. Get your chat ID from @userinfobot.',
    teams: 'Go to Microsoft Teams → Channel → Connectors → Incoming Webhook → Configure.',
    email: 'Enter recipient email address. SMTP settings can be configured in Settings.',
    generic: 'Enter any HTTP/HTTPS webhook URL. Customize the JSON payload template.'
  };
  return instructions[type] || '';
};

export function AddAppPage({ onSave, onCancel, message, showMessage, editingApp }) {
  const initializeDestinations = () => {
    if (editingApp?.notification_destinations && editingApp.notification_destinations.length > 0) {
      return editingApp.notification_destinations.map(dest => ({
        type: dest.type || '',
        webhook_url: dest.webhook_url || '',
        bot_token: dest.bot_token || '',
        chat_id: dest.chat_id || '',
        email: dest.email || '',
        smtp_host: dest.smtp_host || '',
        smtp_port: dest.smtp_port || '',
        smtp_user: dest.smtp_user || '',
        smtp_password: dest.smtp_password || '',
        smtp_from: dest.smtp_from || '',
        payload_template: dest.payload_template || ''
      }));
    } else if (editingApp?.webhook_url) {
      return [{ type: 'discord', webhook_url: editingApp.webhook_url }];
    }
    return [{ type: '', webhook_url: '', bot_token: '', chat_id: '', email: '', smtp_host: '', smtp_port: '', smtp_user: '', smtp_password: '', smtp_from: '', payload_template: '' }];
  };

  const [formData, setFormData] = useState({
    name: editingApp?.name || '',
    app_store_id: String(editingApp?.app_store_id ?? ''),
    app_store_country: String(editingApp?.app_store_country ?? 'us').toLowerCase(),
    interval_override: String(editingApp?.interval_override ?? ''),
    enabled: editingApp?.enabled !== false,
    icon_url: editingApp?.icon_url || ''
  });

  const [errors, setErrors] = useState({});
  const [destinations, setDestinations] = useState(initializeDestinations);
  const [fetchingMetadata, setFetchingMetadata] = useState(false);
  const [suggestedName, setSuggestedName] = useState('');
  
  useEffect(() => {
    document.title = editingApp ? 'Edit App - App Watch' : 'Add New App - App Watch';
    
    if (!editingApp) {
      const loadDefaultSettings = async () => {
        try {
          const response = await fetchSettings();
          if (response.ok) {
            const settings = await response.json();
            setFormData(prev => ({
              ...prev,
              enabled: settings.monitoring_enabled_by_default !== false
            }));
          }
        } catch (error) {
          console.error('Error loading settings:', error);
        }
      };
      loadDefaultSettings();
    }
    
    return () => { document.title = 'App Watch'; };
  }, [editingApp]);

  useEffect(() => {
    const appStoreId = formData.app_store_id.trim();
    const appStoreCountry = String(formData.app_store_country ?? 'us').trim().toLowerCase();
    
    if (appStoreId && /^\d+$/.test(appStoreId)) {
      if (
        editingApp &&
        editingApp.app_store_id === appStoreId &&
        String(editingApp.app_store_country ?? 'us').toLowerCase() === appStoreCountry
      ) {
        return;
      }
      
      const timeoutId = setTimeout(async () => {
        setFetchingMetadata(true);
        try {
          const response = await fetchAppMetadata(appStoreId, appStoreCountry);
          if (response.ok) {
            const metadata = await response.json();
            if (metadata.artworkUrl) {
              setFormData(prev => ({ ...prev, icon_url: metadata.artworkUrl }));
            }
            if (metadata.trackName) {
              setSuggestedName(metadata.trackName);
              setFormData(prev => {
                if (!prev.name.trim()) {
                  return { ...prev, name: metadata.trackName };
                }
                return prev;
              });
            }
          } else {
            setSuggestedName('');
            setFormData(prev => ({ ...prev, icon_url: '' }));
          }
        } catch (error) {
          setSuggestedName('');
          setFormData(prev => ({ ...prev, icon_url: '' }));
        } finally {
          setFetchingMetadata(false);
        }
      }, 800);
      
      return () => clearTimeout(timeoutId);
    } else {
      setSuggestedName('');
      setFormData(prev => ({ ...prev, icon_url: '' }));
    }
  }, [formData.app_store_id, formData.app_store_country, editingApp]);

  const validateForm = () => {
    const newErrors = {};
    const appStoreIdVal = String(formData.app_store_id ?? '').trim();
    const appStoreCountryVal = String(formData.app_store_country ?? '').trim().toLowerCase();
    const intervalOverrideVal = String(formData.interval_override ?? '').trim();

    if (!String(formData.name ?? '').trim()) newErrors.name = 'App Name is required';
    if (!appStoreIdVal) {
      newErrors.app_store_id = 'App Store ID is required';
    } else if (!/^\d+$/.test(appStoreIdVal)) {
      newErrors.app_store_id = 'App Store ID must be a number';
    }
    if (!appStoreCountryVal) {
      newErrors.app_store_country = 'App Store country is required';
    } else if (!/^[a-z]{2}$/i.test(appStoreCountryVal)) {
      newErrors.app_store_country = 'Use a 2-letter country code (e.g., us, gb, in)';
    }
    
    destinations.forEach((dest, index) => {
      if (dest.type) {
        if (['discord', 'slack', 'teams', 'generic'].includes(dest.type)) {
          if (!dest.webhook_url || !dest.webhook_url.trim()) {
            newErrors[`dest_${index}_webhook_url`] = `${dest.type.charAt(0).toUpperCase() + dest.type.slice(1)} webhook URL is required`;
          }
        } else if (dest.type === 'telegram') {
          if (!dest.bot_token || !dest.bot_token.trim()) {
            newErrors[`dest_${index}_bot_token`] = 'Telegram bot token is required';
          }
          if (!dest.chat_id || !dest.chat_id.trim()) {
            newErrors[`dest_${index}_chat_id`] = 'Telegram chat ID is required';
          }
        } else if (dest.type === 'email') {
          if (!dest.email || !dest.email.trim()) {
            newErrors[`dest_${index}_email`] = 'Email address is required';
          }
          if (!dest.smtp_host || !dest.smtp_host.trim()) {
            newErrors[`dest_${index}_smtp_host`] = 'SMTP host is required';
          }
        }
      }
    });
    
    if (intervalOverrideVal) {
      if (!/^\d+[hmsd]$/i.test(intervalOverrideVal)) {
        newErrors.interval_override = 'Invalid interval format. Use: 6h, 30m, 1d';
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const isFormValid = () => {
    const name = String(formData.name ?? '').trim();
    const appStoreId = String(formData.app_store_id ?? '').trim();
    const appStoreCountry = String(formData.app_store_country ?? '').trim();
    const intervalOverride = String(formData.interval_override ?? '').trim();
    if (!name || !appStoreId || !/^\d+$/.test(appStoreId)) {
      return false;
    }
    if (!appStoreCountry || !/^[a-z]{2}$/i.test(appStoreCountry)) {
      return false;
    }
    if (intervalOverride && !/^\d+[hmsd]$/i.test(intervalOverride)) {
      return false;
    }
    return true;
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    const nextValue = type === 'checkbox' ? checked : value;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'app_store_country' ? String(nextValue).toLowerCase() : nextValue
    }));
    if (errors[name]) {
      setErrors(prev => { const newErrors = { ...prev }; delete newErrors[name]; return newErrors; });
    }
  };

  const handleDestinationTypeChange = (index, value) => {
    setDestinations(prev => {
      const newDests = [...prev];
      const existing = newDests[index] || {};
      newDests[index] = { 
        type: value, 
        webhook_url: existing.webhook_url || '',
        bot_token: existing.bot_token || '',
        chat_id: existing.chat_id || '',
        email: existing.email || '',
        smtp_host: existing.smtp_host || '',
        smtp_port: existing.smtp_port || '',
        smtp_user: existing.smtp_user || '',
        smtp_password: existing.smtp_password || '',
        smtp_from: existing.smtp_from || '',
        payload_template: existing.payload_template || ''
      };
      
      if (value && index === newDests.length - 1) {
        newDests.push({ type: '', webhook_url: '', bot_token: '', chat_id: '', email: '', smtp_host: '', smtp_port: '', smtp_user: '', smtp_password: '', smtp_from: '', payload_template: '' });
      }
      
      while (newDests.length > 1 && !newDests[newDests.length - 2].type && !newDests[newDests.length - 1].type) {
        newDests.pop();
      }
      
      return newDests;
    });
  };

  const handleDestinationFieldChange = (index, field, value) => {
    setDestinations(prev => {
      const newDests = [...prev];
      newDests[index] = { ...newDests[index], [field]: value };
      return newDests;
    });
    
    const errorKey = `dest_${index}_${field}`;
    if (errors[errorKey]) {
      setErrors(prev => { const newErrors = { ...prev }; delete newErrors[errorKey]; return newErrors; });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      showMessage('Please fill in all required fields correctly', 'error');
      return;
    }

    const notificationDestinations = destinations
      .filter(dest => dest.type)
      .map(dest => {
        const result = { type: dest.type };
        if (['discord', 'slack', 'teams', 'generic'].includes(dest.type)) {
          if (dest.webhook_url) result.webhook_url = dest.webhook_url.trim();
          if (dest.type === 'generic' && dest.payload_template) {
            result.payload_template = dest.payload_template.trim();
          }
        } else if (dest.type === 'telegram') {
          if (dest.bot_token) result.bot_token = dest.bot_token.trim();
          if (dest.chat_id) result.chat_id = dest.chat_id.trim();
        } else if (dest.type === 'email') {
          if (dest.email) result.email = dest.email.trim();
          if (dest.smtp_host) result.smtp_host = dest.smtp_host.trim();
          if (dest.smtp_port) result.smtp_port = dest.smtp_port.trim();
          if (dest.smtp_user) result.smtp_user = dest.smtp_user.trim();
          if (dest.smtp_password) result.smtp_password = dest.smtp_password.trim();
          if (dest.smtp_from) result.smtp_from = dest.smtp_from.trim();
        }
        return result;
      });

    const submitData = {
      ...formData,
      app_store_country: String(formData.app_store_country ?? 'us').trim().toLowerCase() || 'us',
      notification_destinations: notificationDestinations
    };
    
    if (editingApp) submitData.id = editingApp.id;
    await onSave(submitData);
  };

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">{editingApp ? 'Edit App' : 'Add New App'}</h1>
          <p className="page-subtitle">{editingApp ? 'Update app monitoring settings' : 'Configure a new app to monitor'}</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-secondary" onClick={onCancel}>
            <Icons.ArrowLeft /> Back
          </button>
        </div>
      </div>

      <div className="page-content">
        <div className="form-page">
          {message && (
            <div className={`alert alert-${message.type}`}>
              {message.text}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">App Details</h3>
              </div>
              <div className="card-body">
                <div className="form-group">
                  <label className="form-label">App Name <span className="required">*</span></label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    placeholder={suggestedName || "Enter your app name"}
                    className={`form-input ${errors.name ? 'error' : ''}`}
                  />
                  {suggestedName && !formData.name && (
                    <span className="form-hint">Suggested: {suggestedName}</span>
                  )}
                  {fetchingMetadata && <span className="form-hint">Fetching app info...</span>}
                  {errors.name && <span className="form-error">{errors.name}</span>}
                </div>

                <div className="form-group">
                  <label className="form-label">App Store ID <span className="required">*</span></label>
                  <input
                    type="text"
                    name="app_store_id"
                    value={formData.app_store_id}
                    onChange={handleChange}
                    placeholder="e.g., 123456789"
                    className={`form-input ${errors.app_store_id ? 'error' : ''}`}
                    disabled={fetchingMetadata}
                  />
                  <span className="form-hint">Find this in the App Store URL: apps.apple.com/app/id<strong>123456789</strong></span>
                  {errors.app_store_id && <span className="form-error">{errors.app_store_id}</span>}
                </div>

                <div className="form-group">
                  <label className="form-label">App Store Country <span className="required">*</span></label>
                  <input
                    type="text"
                    name="app_store_country"
                    value={formData.app_store_country}
                    onChange={handleChange}
                    placeholder="us"
                    className={`form-input ${errors.app_store_country ? 'error' : ''}`}
                    maxLength={2}
                  />
                  <span className="form-hint">2-letter storefront code. Default is <code>us</code> if unchanged.</span>
                  {errors.app_store_country && <span className="form-error">{errors.app_store_country}</span>}
                </div>

                <div className="form-group">
                  <label className="form-label">Check Interval (optional)</label>
                  <input
                    type="text"
                    name="interval_override"
                    value={formData.interval_override}
                    onChange={handleChange}
                    placeholder="e.g., 6h, 30m, 1d"
                    className={`form-input ${errors.interval_override ? 'error' : ''}`}
                  />
                  <span className="form-hint">Override default interval. Leave empty for default (12h).</span>
                  {errors.interval_override && <span className="form-error">{errors.interval_override}</span>}
                </div>

                <div className="form-group">
                  <div className="form-checkbox-group">
                    <input
                      type="checkbox"
                      id="enabled"
                      name="enabled"
                      checked={formData.enabled}
                      onChange={handleChange}
                      className="form-checkbox"
                    />
                    <label htmlFor="enabled" className="form-checkbox-label">Enable Monitoring</label>
                  </div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Notification Destinations</h3>
              </div>
              <div className="card-body">
                <p style={{ marginBottom: '20px', color: 'var(--text-muted)', fontSize: '14px' }}>
                  Add one or more notification destinations. Leave empty to skip notifications.
                </p>

                {destinations.map((dest, index) => (
                  <div key={index} className="destination-card">
                    <div className="form-group">
                      <label className="form-label">
                        {index === 0 ? 'Destination Type' : `Destination ${index + 1}`}
                      </label>
                      <select
                        value={dest.type}
                        onChange={(e) => handleDestinationTypeChange(index, e.target.value)}
                        className="form-select"
                      >
                        <option value="">Select destination (optional)</option>
                        <option value="discord">Discord</option>
                        <option value="slack">Slack</option>
                        <option value="telegram">Telegram</option>
                        <option value="teams">Microsoft Teams</option>
                        <option value="email">Email (SMTP)</option>
                        <option value="generic">Generic Webhook</option>
                      </select>
                      {dest.type && (
                        <span className="form-hint">{getWebhookInstructions(dest.type)}</span>
                      )}
                    </div>
                    
                    {dest.type === 'discord' && (
                      <div className="form-group">
                        <label className="form-label">Webhook URL <span className="required">*</span></label>
                        <input
                          type="url"
                          value={dest.webhook_url || ''}
                          onChange={(e) => handleDestinationFieldChange(index, 'webhook_url', e.target.value)}
                          placeholder="https://discord.com/api/webhooks/..."
                          className={`form-input ${errors[`dest_${index}_webhook_url`] ? 'error' : ''}`}
                        />
                        {errors[`dest_${index}_webhook_url`] && <span className="form-error">{errors[`dest_${index}_webhook_url`]}</span>}
                      </div>
                    )}
                    
                    {dest.type === 'slack' && (
                      <div className="form-group">
                        <label className="form-label">Webhook URL <span className="required">*</span></label>
                        <input
                          type="url"
                          value={dest.webhook_url || ''}
                          onChange={(e) => handleDestinationFieldChange(index, 'webhook_url', e.target.value)}
                          placeholder="https://hooks.slack.com/services/..."
                          className={`form-input ${errors[`dest_${index}_webhook_url`] ? 'error' : ''}`}
                        />
                        {errors[`dest_${index}_webhook_url`] && <span className="form-error">{errors[`dest_${index}_webhook_url`]}</span>}
                      </div>
                    )}
                    
                    {dest.type === 'telegram' && (
                      <>
                        <div className="form-group">
                          <label className="form-label">Bot Token <span className="required">*</span></label>
                          <input
                            type="text"
                            value={dest.bot_token || ''}
                            onChange={(e) => handleDestinationFieldChange(index, 'bot_token', e.target.value)}
                            placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
                            className={`form-input ${errors[`dest_${index}_bot_token`] ? 'error' : ''}`}
                          />
                          {errors[`dest_${index}_bot_token`] && <span className="form-error">{errors[`dest_${index}_bot_token`]}</span>}
                        </div>
                        <div className="form-group">
                          <label className="form-label">Chat ID <span className="required">*</span></label>
                          <input
                            type="text"
                            value={dest.chat_id || ''}
                            onChange={(e) => handleDestinationFieldChange(index, 'chat_id', e.target.value)}
                            placeholder="123456789"
                            className={`form-input ${errors[`dest_${index}_chat_id`] ? 'error' : ''}`}
                          />
                          {errors[`dest_${index}_chat_id`] && <span className="form-error">{errors[`dest_${index}_chat_id`]}</span>}
                        </div>
                      </>
                    )}
                    
                    {dest.type === 'teams' && (
                      <div className="form-group">
                        <label className="form-label">Webhook URL <span className="required">*</span></label>
                        <input
                          type="url"
                          value={dest.webhook_url || ''}
                          onChange={(e) => handleDestinationFieldChange(index, 'webhook_url', e.target.value)}
                          placeholder="https://outlook.office.com/webhook/..."
                          className={`form-input ${errors[`dest_${index}_webhook_url`] ? 'error' : ''}`}
                        />
                        {errors[`dest_${index}_webhook_url`] && <span className="form-error">{errors[`dest_${index}_webhook_url`]}</span>}
                      </div>
                    )}
                    
                    {dest.type === 'email' && (
                      <>
                        <div className="form-group">
                          <label className="form-label">Email Address <span className="required">*</span></label>
                          <input
                            type="email"
                            value={dest.email || ''}
                            onChange={(e) => handleDestinationFieldChange(index, 'email', e.target.value)}
                            placeholder="recipient@example.com"
                            className={`form-input ${errors[`dest_${index}_email`] ? 'error' : ''}`}
                          />
                          {errors[`dest_${index}_email`] && <span className="form-error">{errors[`dest_${index}_email`]}</span>}
                        </div>
                        <div className="form-group">
                          <label className="form-label">SMTP Host <span className="required">*</span></label>
                          <input
                            type="text"
                            value={dest.smtp_host || ''}
                            onChange={(e) => handleDestinationFieldChange(index, 'smtp_host', e.target.value)}
                            placeholder="smtp.gmail.com"
                            className={`form-input ${errors[`dest_${index}_smtp_host`] ? 'error' : ''}`}
                          />
                          <span className="form-hint">Can also be set in Settings for all apps.</span>
                          {errors[`dest_${index}_smtp_host`] && <span className="form-error">{errors[`dest_${index}_smtp_host`]}</span>}
                        </div>
                      </>
                    )}
                    
                    {dest.type === 'generic' && (
                      <>
                        <div className="form-group">
                          <label className="form-label">Webhook URL <span className="required">*</span></label>
                          <input
                            type="url"
                            value={dest.webhook_url || ''}
                            onChange={(e) => handleDestinationFieldChange(index, 'webhook_url', e.target.value)}
                            placeholder="https://example.com/webhook"
                            className={`form-input ${errors[`dest_${index}_webhook_url`] ? 'error' : ''}`}
                          />
                          {errors[`dest_${index}_webhook_url`] && <span className="form-error">{errors[`dest_${index}_webhook_url`]}</span>}
                        </div>
                        <div className="form-group">
                          <label className="form-label">Payload Template (JSON, optional)</label>
                          <textarea
                            value={dest.payload_template || ''}
                            onChange={(e) => handleDestinationFieldChange(index, 'payload_template', e.target.value)}
                            placeholder='{"app": "{{app_name}}", "version": "{{version}}"}'
                            rows="3"
                            className="form-input"
                            style={{ fontFamily: 'monospace' }}
                          />
                          <span className="form-hint">Use: {'{{app_name}}'}, {'{{version}}'}, {'{{release_notes}}'}, {'{{formatted_content}}'}</span>
                        </div>
                      </>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {!isFormValid() && (() => {
              const name = String(formData.name ?? '').trim();
              const appStoreId = String(formData.app_store_id ?? '').trim();
              const appStoreCountry = String(formData.app_store_country ?? '').trim();
              const intervalOverride = String(formData.interval_override ?? '').trim();
              const missing = [];
              if (!name) missing.push('App Name');
              if (!appStoreId) missing.push('App Store ID');
              else if (!/^\d+$/.test(appStoreId)) missing.push('App Store ID must be numbers only');
              if (!appStoreCountry) missing.push('App Store Country');
              else if (!/^[a-z]{2}$/i.test(appStoreCountry)) missing.push('App Store Country must be a 2-letter code like us, gb, in');
              if (intervalOverride && !/^\d+[hmsd]$/i.test(intervalOverride)) missing.push('Check Interval: use format like 6h, 30m, 1d (no spaces)');
              return missing.length > 0 ? (
                <div className="alert alert-warning" style={{ marginBottom: '16px' }}>
                  Fill in the required fields above to enable Save: {missing.join('; ')}.
                </div>
              ) : null;
            })()}
            <div className="form-actions">
              <button
                type="submit"
                className="btn btn-primary btn-lg"
                disabled={!isFormValid()}
                title={!isFormValid() ? 'Required: App Name, App Store ID (numbers only), and App Store Country (2 letters). If you use Check Interval, use format like 6h, 30m, or 1d.' : undefined}
              >
                <Icons.Check /> {editingApp ? 'Update App' : 'Save App'}
              </button>
              <button type="button" className="btn btn-secondary btn-lg" onClick={onCancel}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
