import { ApiError, getApiBase, apiRequest } from './client';

describe('client.js', () => {
  describe('ApiError', () => {
    test('constructs with message and options', () => {
      const err = new ApiError('Not found', { status: 404, data: { error: 'Missing' } });
      expect(err.name).toBe('ApiError');
      expect(err.message).toBe('Not found');
      expect(err.status).toBe(404);
      expect(err.data).toEqual({ error: 'Missing' });
    });

    test('retains cause when provided', () => {
      const original = new Error('Original network failure');
      const err = new ApiError('Wrapped error', { cause: original });
      expect(err.cause).toBe(original);
    });
  });

  describe('getApiBase', () => {
    test('returns origin if no REACT_APP_API_BASE env set', () => {
      const originalEnv = process.env.REACT_APP_API_BASE;
      delete process.env.REACT_APP_API_BASE;

      expect(getApiBase()).toBe(window.location.origin);

      if (originalEnv) process.env.REACT_APP_API_BASE = originalEnv;
    });

    test('strips trailing slashes from REACT_APP_API_BASE env var', () => {
      const originalEnv = process.env.REACT_APP_API_BASE;
      process.env.REACT_APP_API_BASE = 'https://api.example.com/';

      expect(getApiBase()).toBe('https://api.example.com');

      if (originalEnv) process.env.REACT_APP_API_BASE = originalEnv;
      else delete process.env.REACT_APP_API_BASE;
    });
  });

  describe('apiRequest', () => {
    afterEach(() => {
      jest.restoreAllMocks();
    });

    test('makes successful GET request and returns status and parsed JSON data', async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        status: 200,
        text: () => Promise.resolve(JSON.stringify({ success: true, count: 5 })),
      });

      const result = await apiRequest('/api/apps');
      expect(result.status).toBe(200);
      expect(result.data).toEqual({ success: true, count: 5 });
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/apps'),
        expect.any(Object)
      );
    });

    test('serializes json parameter and sets Content-Type header on POST request', async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        status: 201,
        text: () => Promise.resolve(JSON.stringify({ id: 'app-123' })),
      });

      const result = await apiRequest('/api/apps', {
        method: 'POST',
        json: { name: 'Test App', platform: 'ios' },
      });

      expect(result.status).toBe(201);
      expect(result.data).toEqual({ id: 'app-123' });

      const [, callOptions] = global.fetch.mock.calls[0];
      expect(callOptions.body).toBe(JSON.stringify({ name: 'Test App', platform: 'ios' }));
      expect(callOptions.headers.get('Content-Type')).toBe('application/json');
    });

    test('throws ApiError with error message from response data on HTTP failure', async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        text: () => Promise.resolve(JSON.stringify({ error: 'App Store ID must be a number' })),
      });

      await expect(apiRequest('/api/apps', { method: 'POST' })).rejects.toThrow('App Store ID must be a number');
    });

    test('throws ApiError with network error message when fetch rejects', async () => {
      global.fetch = jest.fn().mockRejectedValue(new Error('Failed to fetch'));

      await expect(apiRequest('/api/apps')).rejects.toThrow('Failed to fetch');
    });
  });
});
