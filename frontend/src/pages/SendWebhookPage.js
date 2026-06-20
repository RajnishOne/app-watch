import React, { useState, useEffect } from 'react';
import { Icons } from '../components/Icons';
import { fetchWebhooksList, sendWebhooksRequest } from '../api';

export function SendWebhookPage({ onCancel, message, showMessage }) {
  const [customMessage, setCustomMessage] = useState('');
  const [selectedWebhooks, setSelectedWebhooks] = useState([]);
  const [newWebhookUrls, setNewWebhookUrls] = useState([]);
  const [newWebhookUrl, setNewWebhookUrl] = useState('');
  const [availableWebhooks, setAvailableWebhooks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    loadWebhooks();
  }, []);

  const loadWebhooks = async () => {
    setLoading(true);
    try {
      const data = await fetchWebhooksList();
      setAvailableWebhooks(data.webhooks || []);
    } catch (error) {
      showMessage('Error loading webhooks', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleWebhookToggle = (webhookId) => {
    setSelectedWebhooks(prev => {
      if (prev.includes(webhookId)) {
        return prev.filter(id => id !== webhookId);
      } else {
        return [...prev, webhookId];
      }
    });
  };

  const handleAddNewWebhook = () => {
    const url = newWebhookUrl.trim();
    if (!url) {
      setErrors({ newWebhook: 'Webhook URL is required' });
      return;
    }
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      setErrors({ newWebhook: 'Webhook URL must start with http:// or https://' });
      return;
    }
    
    // Add to new webhook URLs list
    if (!newWebhookUrls.includes(url)) {
      setNewWebhookUrls(prev => [...prev, url]);
      setNewWebhookUrl('');
      setErrors({});
    } else {
      setErrors({ newWebhook: 'This webhook URL is already added' });
    }
  };

  const handleRemoveNewWebhook = (url) => {
    setNewWebhookUrls(prev => prev.filter(u => u !== url));
  };

  const handleSend = async (e) => {
    e.preventDefault();
    
    if (!customMessage.trim()) {
      setErrors({ message: 'Message is required' });
      showMessage('Please enter a message', 'error');
      return;
    }

    if (selectedWebhooks.length === 0 && newWebhookUrls.length === 0) {
      setErrors({ webhooks: 'Please select at least one webhook or add a new one' });
      showMessage('Please select at least one webhook or add a new one', 'error');
      return;
    }

    setSending(true);
    setErrors({});

    try {
      // Collect webhook URLs from selected existing webhooks
      const webhookUrls = selectedWebhooks.map(id => {
        const webhook = availableWebhooks.find(w => w.id === id);
        return webhook ? webhook.webhook_url : null;
      }).filter(url => url !== null);

      // Add new webhook URLs
      webhookUrls.push(...newWebhookUrls);

      if (webhookUrls.length === 0) {
        showMessage('No valid webhooks selected', 'error');
        setSending(false);
        return;
      }

      const data = await sendWebhooksRequest({
        message: customMessage.trim(),
        webhook_urls: webhookUrls
      });

      if (data.success) {
        showMessage(data.message || 'Message sent successfully', 'success');
        setCustomMessage('');
        setSelectedWebhooks([]);
        setNewWebhookUrls([]);
        setNewWebhookUrl('');
      } else {
        showMessage(data.error || 'Failed to send message', 'error');
      }
    } catch (error) {
      showMessage('Error sending message: ' + error.message, 'error');
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Broadcast</h1>
          <p className="page-subtitle">Send a custom message to your webhooks</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-secondary" onClick={onCancel}>
            <Icons.ArrowLeft /> Back
          </button>
        </div>
      </div>

      <div className="page-content">
        <div className="form-page">
          <form onSubmit={handleSend}>
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Message</h3>
              </div>
              <div className="card-body">
                <div className="form-group">
                  <label className="form-label">Custom Message <span className="required">*</span></label>
                  <textarea
                    value={customMessage}
                    onChange={(e) => {
                      setCustomMessage(e.target.value);
                      if (errors.message) {
                        setErrors(prev => ({ ...prev, message: '' }));
                      }
                    }}
                    placeholder="Enter your message here... (e.g., 'Hello' or a full paragraph)"
                    rows="6"
                    className={`form-input ${errors.message ? 'error' : ''}`}
                    style={{ resize: 'vertical' }}
                  />
                  <span className="form-hint">Write your message here...</span>
                  {errors.message && <span className="form-error">{errors.message}</span>}
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Select Webhooks</h3>
              </div>
              <div className="card-body">
                {errors.webhooks && <span className="form-error">{errors.webhooks}</span>}
                
                {loading ? (
                  <div className="loading">
                    <div className="loading-spinner"></div>
                    <span>Loading webhooks...</span>
                  </div>
                ) : (
                  <>
                    {availableWebhooks.length > 0 && (
                      <div className="form-group">
                        <label className="form-label">Existing Webhooks</label>
                        <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '12px' }}>
                          {availableWebhooks.map(webhook => (
                            <div key={webhook.id} style={{ marginBottom: '8px' }}>
                              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                                <input
                                  type="checkbox"
                                  checked={selectedWebhooks.includes(webhook.id)}
                                  onChange={() => handleWebhookToggle(webhook.id)}
                                  style={{ cursor: 'pointer' }}
                                />
                                <span style={{ flex: 1 }}>
                                  <strong>{webhook.label}</strong>
                                  <br />
                                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{webhook.webhook_url}</span>
                                </span>
                              </label>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="form-group" style={{ marginTop: '20px' }}>
                      <label className="form-label">Add New Webhook</label>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <input
                          type="url"
                          value={newWebhookUrl}
                          onChange={(e) => {
                            setNewWebhookUrl(e.target.value);
                            if (errors.newWebhook) {
                              setErrors(prev => ({ ...prev, newWebhook: '' }));
                            }
                          }}
                          placeholder="https://discord.com/api/webhooks/... or any webhook URL"
                          className={`form-input ${errors.newWebhook ? 'error' : ''}`}
                          style={{ flex: 1 }}
                        />
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={handleAddNewWebhook}
                        >
                          Add
                        </button>
                      </div>
                      {errors.newWebhook && <span className="form-error">{errors.newWebhook}</span>}
                      <span className="form-hint">Add a new webhook URL to send the message to.</span>
                    </div>

                    {newWebhookUrls.length > 0 && (
                      <div className="form-group">
                        <label className="form-label">New Webhooks Added</label>
                        {newWebhookUrls.map((url, index) => (
                          <div key={index} style={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            justifyContent: 'space-between',
                            padding: '12px', 
                            background: 'var(--bg-hover)', 
                            borderRadius: '8px', 
                            marginBottom: '8px',
                            fontSize: '14px' 
                          }}>
                            <span style={{ flex: 1, wordBreak: 'break-all' }}>{url}</span>
                            <button
                              type="button"
                              onClick={() => handleRemoveNewWebhook(url)}
                              style={{
                                marginLeft: '8px',
                                padding: '4px 8px',
                                background: 'var(--accent-primary)',
                                border: 'none',
                                borderRadius: '4px',
                                color: 'var(--bg-primary)',
                                cursor: 'pointer',
                                fontSize: '12px'
                              }}
                            >
                              Remove
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {availableWebhooks.length === 0 && !loading && (
                      <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                        <p>No webhooks found in your apps.</p>
                        <p style={{ fontSize: '14px', marginTop: '8px' }}>Add a new webhook URL above or configure webhooks in your apps.</p>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>

            <div className="form-actions">
              <button type="submit" className="btn btn-primary btn-lg" disabled={sending || !customMessage.trim() || (selectedWebhooks.length === 0 && newWebhookUrls.length === 0)}>
                {sending ? (
                  <>
                    <div className="loading-spinner" style={{ width: '16px', height: '16px', marginRight: '8px' }}></div>
                    Sending...
                  </>
                ) : (
                  <>
                    <Icons.Send /> Send Message
                  </>
                )}
              </button>
              <button type="button" className="btn btn-secondary btn-lg" onClick={onCancel} disabled={sending}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
