export const API_BASE = window.location.origin;

export function fetchApps() {
  return fetch(`${API_BASE}/api/apps`);
}

export function deleteApp(appId) {
  return fetch(`${API_BASE}/api/apps/${appId}`, {
    method: 'DELETE'
  });
}

export function checkApp(appId) {
  return fetch(`${API_BASE}/api/apps/${appId}/check`, {
    method: 'POST'
  });
}

export function postApp(appId) {
  return fetch(`${API_BASE}/api/apps/${appId}/post`, {
    method: 'POST'
  });
}

export function saveAppRequest(appId, formData) {
  const url = appId ? `${API_BASE}/api/apps/${appId}` : `${API_BASE}/api/apps`;
  const method = appId ? 'PUT' : 'POST';
  return fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData)
  });
}

export function fetchSettings() {
  return fetch(`${API_BASE}/api/settings`);
}

export function putSettings(settingsToSave) {
  return fetch(`${API_BASE}/api/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settingsToSave)
  });
}

export function fetchAppMetadata(appStoreId) {
  return fetch(`${API_BASE}/api/apps/metadata/${appStoreId}`);
}

export function fetchAuthStatus() {
  return fetch(`${API_BASE}/api/auth/status`);
}

export function regenerateApiKeyRequest() {
  return fetch(`${API_BASE}/api/auth/api-key/regenerate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
}

export function fetchHistoryQuery(queryString) {
  return fetch(`${API_BASE}/api/history?${queryString}`);
}

export function fetchWebhooksList() {
  return fetch(`${API_BASE}/api/webhooks/list`);
}

export function sendWebhooksRequest(body) {
  return fetch(`${API_BASE}/api/webhooks/send`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  });
}
