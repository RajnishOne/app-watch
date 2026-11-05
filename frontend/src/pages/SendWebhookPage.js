import React, { useState, useEffect, useCallback } from 'react';
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

  const loadWebhooks = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchWebhooksList();
      setAvailableWebhooks(data.webhooks || []);
    } catch (error) {
      showMessage('Error loading webhooks', 'error');
    } finally {
      setLoading(false);
    }
  }, [showMessage]);

  useEffect(() => {
    loadWebhooks();
    document.title = 'Broadcast - App Watch';
    return () => { document.title = 'App Watch'; };
  }, [loadWebhooks]);

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
      const webhookUrls = selectedWebhooks.map(id => {
        const webhook = availableWebhooks.find(w => w.id === id);
        return webhook ? webhook.webhook_url : null;
      }).filter(url => url !== null);

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
          <p className="page-subtitle">Broadcast notification messages across configured webhook channels</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-secondary" onClick={onCancel}>
            <Icons.ArrowLeft />
            <span>Back</span>
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
                  <label className="form-label">Broadcast message <span className="required">*</span></label>
                  <textarea
                    value={customMessage}
                    onChange={(e) => {
                      setCustomMessage(e.target.value);
                      if (errors.message) {
                        setErrors(prev => ({ ...prev, message: '' }));
                      }
                    }}
                    placeholder="Enter message text to broadcast…"
                    rows="5"
                    className={`form-input font-mono ${errors.message ? 'error' : ''}`}
                    style={{ resize: 'vertical' }}
                  />
                  {errors.message && <span className="form-error">{errors.message}</span>}
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Target webhooks</h3>
              </div>
              <div className="card-body">
                {errors.webhooks && <span className="form-error">{errors.webhooks}</span>}
                
                {loading ? (
                  <div className="loading">
                    <div className="loading-spinner"></div>
                    <span>Loading webhooks…</span>
                  </div>
                ) : (
                  <>
                    {availableWebhooks.length > 0 && (
                      <div className="form-group">
                        <label className="form-label">Configured destinations</label>
                        <div className="webhook-selector-list">
                          {availableWebhooks.map(webhook => (
                            <label key={webhook.id} className="webhook-select-item">
                              <input
                                type="checkbox"
                                checked={selectedWebhooks.includes(webhook.id)}
                                onChange={() => handleWebhookToggle(webhook.id)}
                                className="form-checkbox"
                              />
                              <div className="webhook-select-content">
                                <span className="webhook-select-label">{webhook.label}</span>
                                <span className="webhook-select-url font-mono">{webhook.webhook_url}</span>
                              </div>
                            </label>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="form-group">
                      <label className="form-label">Add custom webhook</label>
                      <div className="input-with-button">
                        <input
                          type="url"
                          value={newWebhookUrl}
                          onChange={(e) => {
                            setNewWebhookUrl(e.target.value);
                            if (errors.newWebhook) {
                              setErrors(prev => ({ ...prev, newWebhook: '' }));
                            }
                          }}
                          placeholder="https://…"
                          className={`form-input font-mono ${errors.newWebhook ? 'error' : ''}`}
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
                    </div>

                    {newWebhookUrls.length > 0 && (
                      <div className="form-group">
                        <label className="form-label">Additional recipients</label>
                        <div className="new-webhooks-list">
                          {newWebhookUrls.map((url, index) => (
                            <div key={index} className="new-webhook-row">
                              <span className="font-mono text-secondary text-truncate">{url}</span>
                              <button
                                type="button"
                                className="btn btn-subtle-danger btn-sm"
                                onClick={() => handleRemoveNewWebhook(url)}
                              >
                                Remove
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {availableWebhooks.length === 0 && !loading && newWebhookUrls.length === 0 && (
                      <div className="empty-subtext">
                        <p>No webhooks configured yet. Add a URL above or configure notification profiles in Settings.</p>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>

            <div className="form-actions">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={sending || !customMessage.trim() || (selectedWebhooks.length === 0 && newWebhookUrls.length === 0)}
              >
                {sending ? 'Sending…' : 'Send broadcast'}
              </button>
              <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={sending}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
