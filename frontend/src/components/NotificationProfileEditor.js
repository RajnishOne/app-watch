import React from 'react';

export const NOTIFICATION_TYPES = [
  { value: 'discord', label: 'Discord' },
  { value: 'slack', label: 'Slack' },
  { value: 'telegram', label: 'Telegram' },
  { value: 'teams', label: 'Microsoft Teams' },
  { value: 'email', label: 'Email (SMTP)' },
  { value: 'generic', label: 'Generic Webhook' }
];

const ProfileInput = ({ label, field, profile, index, onChange, errors, type = 'text', placeholder = '', required = false }) => {
  const error = errors[`profile_${index}_${field}`];
  return (
    <div className="form-group">
      <label className="form-label">{label} {required && <span className="required">*</span>}</label>
      <input
        type={type}
        value={profile[field] || ''}
        onChange={(event) => onChange(index, field, event.target.value)}
        placeholder={placeholder}
        className={`form-input ${error ? 'error' : ''}`}
      />
      {error && <span className="form-error">{error}</span>}
    </div>
  );
};

export function NotificationProfileEditor({ profile, index, onChange, onRemove, errors, globalTelegramToken, globalSmtpHost }) {
  const webhookPlaceholder = profile.type === 'discord'
    ? 'https://discord.com/api/webhooks/...'
    : profile.type === 'slack'
      ? 'https://hooks.slack.com/services/...'
      : profile.type === 'teams'
        ? 'https://outlook.office.com/webhook/...'
        : 'https://example.com/webhook';

  return (
    <div className="destination-card" style={{ marginBottom: '16px' }}>
      <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
        <div className="form-group" style={{ flex: 1 }}>
          <label className="form-label">Profile Name <span className="required">*</span></label>
          <input
            type="text"
            value={profile.name || ''}
            onChange={(event) => onChange(index, 'name', event.target.value)}
            placeholder="e.g., Main Telegram"
            className={`form-input ${errors[`profile_${index}_name`] ? 'error' : ''}`}
          />
          {errors[`profile_${index}_name`] && <span className="form-error">{errors[`profile_${index}_name`]}</span>}
        </div>
        <button type="button" className="btn btn-secondary" onClick={() => onRemove(index)} style={{ marginTop: '28px' }}>
          Remove
        </button>
      </div>

      <div className="form-group">
        <label className="form-label">Destination Type <span className="required">*</span></label>
        <select value={profile.type || ''} onChange={(event) => onChange(index, 'type', event.target.value)} className="form-select">
          <option value="">Select destination</option>
          {NOTIFICATION_TYPES.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}
        </select>
        {errors[`profile_${index}_type`] && <span className="form-error">{errors[`profile_${index}_type`]}</span>}
      </div>

      {['discord', 'slack', 'teams', 'generic'].includes(profile.type) && (
        <ProfileInput label="Webhook URL" field="webhook_url" profile={profile} index={index} onChange={onChange} errors={errors} type="url" placeholder={webhookPlaceholder} required />
      )}

      {profile.type === 'telegram' && (
        <>
          <ProfileInput label="Bot Token" field="bot_token" profile={profile} index={index} onChange={onChange} errors={errors} type="password" placeholder={globalTelegramToken ? 'Uses the default token when empty' : '123456789:ABCdef...'} required={!globalTelegramToken} />
          {globalTelegramToken && <span className="form-hint" style={{ display: 'block', marginTop: '-12px', marginBottom: '16px' }}>Leave empty to use the default Telegram bot token.</span>}
          <ProfileInput label="Chat ID" field="chat_id" profile={profile} index={index} onChange={onChange} errors={errors} placeholder="-1001234567890_2" required />
          <span className="form-hint" style={{ display: 'block', marginTop: '-12px', marginBottom: '16px' }}>A topic can be specified as chat_id_topic_id.</span>
        </>
      )}

      {profile.type === 'email' && (
        <>
          <ProfileInput label="Recipient Email" field="email" profile={profile} index={index} onChange={onChange} errors={errors} type="email" placeholder="recipient@example.com" required />
          <ProfileInput label="SMTP Host" field="smtp_host" profile={profile} index={index} onChange={onChange} errors={errors} placeholder={globalSmtpHost ? 'Uses the default SMTP host when empty' : 'smtp.gmail.com'} required={!globalSmtpHost} />
          <ProfileInput label="SMTP Port" field="smtp_port" profile={profile} index={index} onChange={onChange} errors={errors} placeholder="587" />
          <ProfileInput label="SMTP Username" field="smtp_user" profile={profile} index={index} onChange={onChange} errors={errors} placeholder="sender@example.com" />
          <ProfileInput label="SMTP Password" field="smtp_password" profile={profile} index={index} onChange={onChange} errors={errors} type="password" />
          <ProfileInput label="From Email" field="smtp_from" profile={profile} index={index} onChange={onChange} errors={errors} type="email" placeholder="sender@example.com" />
        </>
      )}

      {profile.type === 'generic' && (
        <div className="form-group">
          <label className="form-label">Payload Template (JSON, optional)</label>
          <textarea
            value={profile.payload_template || ''}
            onChange={(event) => onChange(index, 'payload_template', event.target.value)}
            placeholder={'{"app": "{{app_name}}", "version": "{{version}}"}'}
            rows="3"
            className={`form-input ${errors[`profile_${index}_payload_template`] ? 'error' : ''}`}
            style={{ fontFamily: 'monospace' }}
          />
          {errors[`profile_${index}_payload_template`] && <span className="form-error">{errors[`profile_${index}_payload_template`]}</span>}
        </div>
      )}
    </div>
  );
}
