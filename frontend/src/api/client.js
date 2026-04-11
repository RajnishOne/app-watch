/**
 * Central HTTP client: base URL, fetch, JSON parse, and API error shaping.
 * Add auth headers here if the app ever requires them again.
 */

export class ApiError extends Error {
  constructor(message, { status, data, cause } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
    if (cause) this.cause = cause;
  }
}

export function getApiBase() {
  const fromEnv = process.env.REACT_APP_API_BASE;
  if (fromEnv && String(fromEnv).trim()) {
    return String(fromEnv).trim().replace(/\/$/, '');
  }
  return window.location.origin;
}

function joinUrl(path) {
  const base = getApiBase().replace(/\/$/, '');
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${base}${p}`;
}

function errorMessageFromBody(data, fallback) {
  if (data && typeof data === 'object') {
    if (typeof data.error === 'string' && data.error.trim()) return data.error.trim();
    if (typeof data.message === 'string' && data.message.trim()) return data.message.trim();
  }
  return fallback;
}

async function readJsonBody(response) {
  const text = await response.text();
  if (!text || !text.trim()) return null;
  try {
    return JSON.parse(text);
  } catch {
    return { _invalidJson: true, raw: text };
  }
}

/**
 * @param {string} path - Absolute path on API host, e.g. "/api/apps" or "/api/history?limit=10"
 * @param {RequestInit & { json?: unknown }} [options] - Standard fetch options; use `json` as shorthand for JSON body
 * @returns {Promise<{ status: number, data: any }>}
 * @throws {ApiError} on network failure or non-OK HTTP status
 */
export async function apiRequest(path, options = {}) {
  const { json, body, headers: initHeaders, ...rest } = options;
  const headers = new Headers(initHeaders || {});

  let fetchBody = body;
  if (json !== undefined) {
    headers.set('Content-Type', headers.get('Content-Type') || 'application/json');
    fetchBody = JSON.stringify(json);
  } else if (
    fetchBody !== undefined &&
    fetchBody !== null &&
    typeof fetchBody === 'object' &&
    !(fetchBody instanceof FormData) &&
    !(fetchBody instanceof Blob) &&
    !(fetchBody instanceof ArrayBuffer)
  ) {
    headers.set('Content-Type', headers.get('Content-Type') || 'application/json');
    fetchBody = JSON.stringify(fetchBody);
  }

  // if (getAuthToken()) headers.set('Authorization', `Bearer ${getAuthToken()}`);

  let response;
  try {
    response = await fetch(joinUrl(path), {
      ...rest,
      headers,
      body: fetchBody,
    });
  } catch (cause) {
    const msg = cause?.message || 'Network error';
    throw new ApiError(msg, { cause });
  }

  const data = await readJsonBody(response);

  if (!response.ok) {
    const fallback = response.statusText || `Request failed (${response.status})`;
    throw new ApiError(errorMessageFromBody(data, fallback), {
      status: response.status,
      data,
    });
  }

  return { status: response.status, data };
}
