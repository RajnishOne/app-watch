import React, { useState } from 'react';
import { Icons } from '../components/Icons';
import { checkApp } from '../api';
import { getHumanReadableError } from '../utils/errors';

export function DashboardPage({ apps, message, onAddApp, onEditApp, onDeleteApp, onCheckApp, onPostApp, checking, posting }) {
  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Apps</h1>
          <p className="page-subtitle">Monitor your iOS and Android apps for new releases</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-primary" onClick={onAddApp}>
            <Icons.Add /> Add App
          </button>
        </div>
      </div>

      <div className="page-content">
        {message && (
          <div className={`alert alert-${message.type}`}>
            {message.text}
          </div>
        )}

        {apps.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📱</div>
            <h3>No apps configured</h3>
            <p>Add your first app to start monitoring for updates</p>
            <button className="btn btn-primary btn-lg" onClick={onAddApp}>
              <Icons.Add /> Add Your First App
            </button>
          </div>
        ) : (
          <div className="apps-grid">
            {apps.map(app => (
              <AppCard
                key={app.id}
                app={app}
                onEdit={onEditApp}
                onDelete={onDeleteApp}
                onCheck={onCheckApp}
                onPost={onPostApp}
                checking={checking[app.id]}
                posting={posting[app.id]}
              />
            ))}
          </div>
        )}
      </div>
    </>
  );
}

export function AppCard({ app, onEdit, onDelete, onCheck, onPost, checking, posting }) {
  const [preview, setPreview] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  const loadPreview = async () => {
    setLoadingPreview(true);
    try {
      const data = await checkApp(app.id);
      if (data.formatted_preview) {
        setPreview(data.formatted_preview);
      } else if (!data.success && data.error) {
        // Silently handle errors in preview - don't show message, just log
        console.error('Error loading preview:', getHumanReadableError(data.error));
      }
    } catch (error) {
      console.error('Error loading preview:', getHumanReadableError(error.message));
    } finally {
      setLoadingPreview(false);
    }
  };

  const getDestinationSummary = () => {
    const destinations = app.notification_destinations || [];
    const hasLegacyWebhook = app.webhook_url && app.webhook_url.trim();
    
    if (destinations.length === 0 && !hasLegacyWebhook) {
      return <span style={{ color: 'var(--text-muted)' }}>Not configured</span>;
    }
    
    if (destinations.length === 0 && hasLegacyWebhook) {
      return '1 Discord webhook';
    }
    
    const validDestinations = destinations.filter(d => {
      if (['discord', 'slack', 'teams', 'generic'].includes(d.type)) {
        return d.webhook_url && d.webhook_url.trim();
      } else if (d.type === 'telegram') {
        return (d.bot_token && d.bot_token.trim()) && (d.chat_id && d.chat_id.trim());
      } else if (d.type === 'email') {
        return d.email && d.email.trim() && (d.smtp_host && d.smtp_host.trim());
      }
      return false;
    });
    
    if (validDestinations.length === 0) {
      return <span style={{ color: 'var(--text-muted)' }}>Not configured</span>;
    }
    
    const counts = {};
    validDestinations.forEach(d => {
      counts[d.type] = (counts[d.type] || 0) + 1;
    });
    
    const parts = [];
    if (counts.discord) parts.push(`${counts.discord} Discord`);
    if (counts.slack) parts.push(`${counts.slack} Slack`);
    if (counts.telegram) parts.push(`${counts.telegram} Telegram`);
    if (counts.teams) parts.push(`${counts.teams} Teams`);
    if (counts.email) parts.push(`${counts.email} Email`);
    if (counts.generic) parts.push(`${counts.generic} Generic`);
    
    return parts.join(', ') || <span style={{ color: 'var(--text-muted)' }}>Not configured</span>;
  };

  return (
    <div className="app-card">
      <div className="app-card-header">
        <img 
          src={app.icon_url || (app.platform === 'android' ? '/androiddefault.png' : '/iosdefault.png')} 
          alt={app.name}
          className="app-icon"
          onError={(e) => { e.target.src = app.platform === 'android' ? '/androiddefault.png' : '/iosdefault.png'; }}
        />
        <div className="app-title-section">
          <div className="app-name" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '14px', opacity: 0.8 }} title={app.platform === 'android' ? 'Android App' : 'iOS App'}>
              {app.platform === 'android' ? '🤖' : '🍎'}
            </span>
            <span style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
              {app.name}
            </span>
          </div>
          <div className="app-store-id">
            {app.platform === 'android' ? 'Package: ' : 'ID: '}{app.app_store_id}
          </div>
        </div>
        <span className={`app-status-badge ${app.enabled ? 'enabled' : 'disabled'}`}>
          {app.enabled ? 'Enabled' : 'Disabled'}
        </span>
      </div>

      <div className="app-card-body">
        <div className="app-info-grid">
          <div className="app-info-item">
            <span className="app-info-label">Current Version</span>
            <span className="app-info-value">{app.current_version || 'Not checked'}</span>
          </div>
          <div className="app-info-item">
            <span className="app-info-label">Last Posted</span>
            <span className="app-info-value">{app.last_posted_version || 'Never'}</span>
          </div>
          <div className="app-info-item">
            <span className="app-info-label">Last Check</span>
            <span className="app-info-value">
              {app.last_check ? new Date(app.last_check).toLocaleString() : 'Never'}
            </span>
          </div>
          <div className="app-info-item">
            <span className="app-info-label">Check Interval</span>
            <span className="app-info-value">{app.interval_override || 'Default (12h)'}</span>
          </div>
          <div className="app-info-item" style={{ gridColumn: '1 / -1' }}>
            <span className="app-info-label">Notifications</span>
            <span className="app-info-value destinations">{getDestinationSummary()}</span>
          </div>
        </div>

        {preview && (
          <div style={{ marginBottom: '16px' }}>
            <div className="app-info-label" style={{ marginBottom: '8px' }}>Preview</div>
            <div className="preview-box">{preview}</div>
          </div>
        )}

        <div className="app-card-actions">
          <button className="btn btn-secondary btn-sm" onClick={() => onCheck(app.id)} disabled={checking || posting}>
            {checking ? 'Checking...' : 'Check'}
          </button>
          <button className="btn btn-success btn-sm" onClick={() => onPost(app.id)} disabled={checking || posting}>
            {posting ? 'Posting...' : 'Post'}
          </button>
          <button className="btn btn-secondary btn-sm" onClick={loadPreview} disabled={loadingPreview}>
            {loadingPreview ? 'Loading...' : 'Preview'}
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => onEdit(app)} disabled={checking || posting}>
            Edit
          </button>
          <button className="btn btn-danger btn-sm" onClick={() => onDelete(app.id)} disabled={checking || posting}>
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
