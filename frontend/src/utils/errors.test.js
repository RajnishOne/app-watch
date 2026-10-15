import { getHumanReadableError } from './errors';

describe('getHumanReadableError', () => {
  test('handles null, undefined, or empty messages', () => {
    expect(getHumanReadableError(null)).toBe('An unknown error occurred');
    expect(getHumanReadableError('')).toBe('An unknown error occurred');
    expect(getHumanReadableError(undefined)).toBe('An unknown error occurred');
  });

  test('converts DNS and name resolution errors', () => {
    expect(getHumanReadableError('Failed to resolve host apps.apple.com')).toContain('Unable to connect to App Store');
    expect(getHumanReadableError('Temporary failure in name resolution')).toContain('Unable to connect to App Store');
    expect(getHumanReadableError('DNS lookup error')).toContain('Unable to connect to App Store');
  });

  test('converts connection and timeout errors', () => {
    expect(getHumanReadableError('Connection refused')).toContain('Connection to App Store failed');
    expect(getHumanReadableError('Connection timeout')).toContain('Connection to App Store failed');
    expect(getHumanReadableError('Request timed out')).toContain('Request timed out');
    expect(getHumanReadableError('Max retries exceeded with url')).toContain('Unable to reach App Store after multiple attempts');
  });

  test('converts HTTP status codes to user-friendly messages', () => {
    expect(getHumanReadableError('Error: 404 Not Found')).toContain('App not found in App Store');
    expect(getHumanReadableError('403 Forbidden')).toContain('Access denied');
    expect(getHumanReadableError('429 Too Many Requests')).toContain('Too many requests');
    expect(getHumanReadableError('500 Internal Server Error')).toContain('App Store server error');
    expect(getHumanReadableError('502 Bad Gateway')).toContain('App Store is temporarily unavailable');
    expect(getHumanReadableError('503 Service Unavailable')).toContain('App Store service is temporarily unavailable');
  });

  test('converts webhook and notification error messages', () => {
    expect(getHumanReadableError('Webhook request failed with status 400')).toContain('Failed to send notification');
    expect(getHumanReadableError('Notification send failed')).toContain('Failed to send notification');
  });

  test('cleans technical details like HTTPSConnectionPool and Caused by', () => {
    const rawError = 'HTTPSConnectionPool(host="itunes.apple.com", port=443): Caused by SSLError()';
    const cleaned = getHumanReadableError(rawError);
    expect(cleaned).not.toContain('HTTPSConnectionPool');
    expect(cleaned).not.toContain('Caused by');
  });

  test('returns standard message if no special pattern matches', () => {
    expect(getHumanReadableError('Some simple custom error')).toBe('Some simple custom error');
  });
});
