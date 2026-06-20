import { apiRequest } from './api/client';

export { apiRequest, getApiBase, ApiError } from './api/client';

export async function fetchApps() {
  const { data } = await apiRequest('/api/apps');
  return data;
}

export async function deleteApp(appId) {
  await apiRequest(`/api/apps/${encodeURIComponent(appId)}`, { method: 'DELETE' });
}

export async function checkApp(appId) {
  const { data } = await apiRequest(`/api/apps/${encodeURIComponent(appId)}/check`, {
    method: 'POST',
  });
  return data;
}

export async function postApp(appId) {
  const { data } = await apiRequest(`/api/apps/${encodeURIComponent(appId)}/post`, {
    method: 'POST',
  });
  return data;
}

export async function saveAppRequest(appId, formData) {
  const path = appId
    ? `/api/apps/${encodeURIComponent(appId)}`
    : '/api/apps';
  const method = appId ? 'PUT' : 'POST';
  const { data } = await apiRequest(path, { method, json: formData });
  return data;
}

export async function fetchSettings() {
  const { data } = await apiRequest('/api/settings');
  return data;
}

export async function putSettings(settingsToSave) {
  const { data } = await apiRequest('/api/settings', {
    method: 'PUT',
    json: settingsToSave,
  });
  return data;
}

/** Resolves to metadata or `null` if the app is unknown or the request fails (soft failure for the form). */
export async function fetchAppMetadata(appStoreId, country = 'us', platform = 'ios') {
  try {
    const normalizedCountry = String(country || 'us').trim().toLowerCase() || 'us';
    const params = new URLSearchParams({ country: normalizedCountry, platform });
    const { data } = await apiRequest(
      `/api/apps/metadata/${encodeURIComponent(String(appStoreId))}?${params.toString()}`
    );
    return data;
  } catch {
    return null;
  }
}

export async function fetchAuthStatus() {
  const { data } = await apiRequest('/api/auth/status');
  return data;
}

export async function regenerateApiKeyRequest() {
  const { data } = await apiRequest('/api/auth/api-key/regenerate', { method: 'POST' });
  return data;
}

export async function fetchHistoryQuery(queryString) {
  const path = queryString ? `/api/history?${queryString}` : '/api/history';
  const { data } = await apiRequest(path);
  return data;
}

export async function fetchWebhooksList() {
  const { data } = await apiRequest('/api/webhooks/list');
  return data;
}

export async function sendWebhooksRequest(body) {
  const { data } = await apiRequest('/api/webhooks/send', {
    method: 'POST',
    json: body,
  });
  return data;
}
