import React, { useEffect, useState } from 'react';
import { Icons } from '../components/Icons';
import { checkApp, fetchSettings } from '../api';
import { getHumanReadableError } from '../utils/errors';

export function DashboardPage({ apps, message, onAddApp, onEditApp, onDeleteApp, onCheckApp, onPostApp, checking, posting }) {
  const [notificationProfiles, setNotificationProfiles] = useState([]);

  useEffect(() => {
    let cancelled = false;
    fetchSettings()
      .then(settings => {
        if (!cancelled) {
          setNotificationProfiles(Array.isArray(settings.notification_profiles) ? settings.notification_profiles : []);
        }
      })
      .catch(error => console.error('Error loading notification profiles:', error));
    return () => { cancelled = true; };
  }, []);

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Apps</h1>
          <p className="page-subtitle">Track release versions and configure update broadcasts</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-primary" onClick={onAddApp}>
            <Icons.Add />
            <span>Add app</span>
          </button>
        </div>
      </div>

      <div className="page-content">
        {apps.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">
              <Icons.Apps />
            </div>
            <h3>No apps configured</h3>
            <p>Add an iOS App Store or Google Play Store app to start tracking updates</p>
            <button className="btn btn-primary" onClick={onAddApp}>
              <Icons.Add />
              <span>Add app</span>
            </button>
          </div>
        ) : (
          <div className="apps-grid">
            {apps.map(app => (
              <AppCard
                key={app.id}
                app={app}
                notificationProfiles={notificationProfiles}
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

export function AppCard({ app, notificationProfiles = [], onEdit, onDelete, onCheck, onPost, checking, posting }) {
  const [preview, setPreview] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  const loadPreview = async () => {
    setLoadingPreview(true);
    try {
      const data = await checkApp(app.id);
      if (data.formatted_preview) {
        setPreview(data.formatted_preview);
      } else if (!data.success && data.error) {
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
      return <span className="text-muted">Not configured</span>;
    }
    
    if (destinations.length === 0 && hasLegacyWebhook) {
      return '1 Discord webhook';
    }
    
    const validDestinations = destinations.filter(d => {
      if (d.profile_id) return true;
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
      return <span className="text-muted">Not configured</span>;
    }
    
    const counts = {};
    const profileNames = [];
    validDestinations.forEach(d => {
      if (d.profile_id) {
        const profile = notificationProfiles.find(item => item.id === d.profile_id);
        profileNames.push(profile?.name || `Missing profile (${d.profile_id})`);
      } else {
        counts[d.type] = (counts[d.type] || 0) + 1;
      }
    });
    
    const parts = [];
    if (counts.discord) parts.push(`${counts.discord} Discord`);
    if (counts.slack) parts.push(`${counts.slack} Slack`);
    if (counts.telegram) parts.push(`${counts.telegram} Telegram`);
    if (counts.teams) parts.push(`${counts.teams} Teams`);
    if (counts.email) parts.push(`${counts.email} Email`);
    if (counts.generic) parts.push(`${counts.generic} Generic`);
    parts.push(...profileNames);
    
    return parts.join(', ') || <span className="text-muted">Not configured</span>;
  };

  const isAndroid = app.platform === 'android';

  return (
    <div className="app-card">
      <div className="app-card-header">
        <img 
          src={app.icon_url || (isAndroid ? '/androiddefault.png' : '/iosdefault.png')} 
          alt=""
          className="app-icon"
          onError={(e) => { e.target.src = isAndroid ? '/androiddefault.png' : '/iosdefault.png'; }}
        />
        <div className="app-title-section">
          <div className="app-name">
            <span className="app-platform-mark" title={isAndroid ? 'Android' : 'iOS'}>
              {isAndroid ? <Icons.Android /> : <Icons.Apple />}
            </span>
            <span className="app-name-text">
              {app.name}
            </span>
          </div>
          <div className="app-store-id font-mono">
            {isAndroid ? 'pkg:' : 'id:'}{app.app_store_id}
          </div>
        </div>
        <span className={`app-status-badge ${app.enabled ? 'enabled' : 'disabled'}`}>
          <span className="status-dot"></span>
          {app.enabled ? 'Active' : 'Paused'}
        </span>
      </div>

      <div className="app-card-body">
        <div className="app-info-grid">
          <div className="app-info-item">
            <span className="app-info-label">Current version</span>
            <span className="app-info-value font-mono">{app.current_version ? `v${app.current_version.replace(/^v/, '')}` : 'Not checked'}</span>
          </div>
          <div className="app-info-item">
            <span className="app-info-label">Last posted</span>
            <span className="app-info-value font-mono">{app.last_posted_version ? `v${app.last_posted_version.replace(/^v/, '')}` : 'Never'}</span>
          </div>
          <div className="app-info-item">
            <span className="app-info-label">Last check</span>
            <span className="app-info-value font-mono">
              {app.last_check ? new Date(app.last_check).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) : 'Never'}
            </span>
          </div>
          <div className="app-info-item">
            <span className="app-info-label">Check interval</span>
            <span className="app-info-value font-mono">{app.interval_override || 'Default (12h)'}</span>
          </div>
          <div className="app-info-item app-info-full">
            <span className="app-info-label">Notifications</span>
            <span className="app-info-value destinations">{getDestinationSummary()}</span>
          </div>
        </div>

        {preview && (
          <div className="preview-container">
            <div className="app-info-label">Preview</div>
            <pre className="preview-box font-mono">{preview}</pre>
          </div>
        )}

        <div className="app-card-actions">
          <div className="app-card-actions-group">
            <button className="btn btn-secondary btn-sm" onClick={() => onCheck(app.id)} disabled={checking || posting}>
              <Icons.Refresh />
              <span>{checking ? 'Checking…' : 'Check'}</span>
            </button>
            <button className="btn btn-primary btn-sm" onClick={() => onPost(app.id)} disabled={checking || posting}>
              <Icons.Send />
              <span>{posting ? 'Posting…' : 'Post'}</span>
            </button>
          </div>
          <div className="app-card-actions-group">
            <button className="btn btn-secondary btn-sm" onClick={loadPreview} disabled={loadingPreview}>
              <span>{loadingPreview ? 'Loading…' : 'Preview'}</span>
            </button>
            <button className="btn btn-secondary btn-sm" onClick={() => onEdit(app)} disabled={checking || posting}>
              <span>Edit</span>
            </button>
            <button className="btn btn-subtle-danger btn-sm" onClick={() => onDelete(app.id)} disabled={checking || posting}>
              <span>Delete</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
