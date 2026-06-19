import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

const originalFetch = global.fetch;

describe('api client', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
    localStorage.clear();
    vi.resetModules();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.clearAllMocks();
  });

  it('should make a GET request and return JSON', async () => {
    const { api } = await import('../api');
    const mockResponse = { id: '1', username: 'test' };
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    });

    const result = await api.auth.me();

    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/auth/me', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      body: undefined,
    });
    expect(result).toEqual(mockResponse);
  });

  it('should stringify body for POST requests', async () => {
    const { api } = await import('../api');
    const mockResponse = { access_token: '123', user: {} };
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    });

    const body = { username: 'test', password: 'password' };
    await api.auth.login(body);

    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
  });

  it('should inject token from localStorage if present', async () => {
    const { api } = await import('../api');
    localStorage.setItem('token', 'test-token');
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({}),
    });

    await api.auth.me();

    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/auth/me', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer test-token',
      },
      body: undefined,
    });
  });

  it('should inject demo token if DEMO_MODE is true and no token in localStorage', async () => {
    process.env.NEXT_PUBLIC_DEMO_MODE = 'true';
    const { api } = await import('../api');

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({}),
    });

    await api.auth.me();

    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/auth/me', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer demo-token',
      },
      body: undefined,
    });

    // Clean up
    delete process.env.NEXT_PUBLIC_DEMO_MODE;
  });

  it('should return empty object for 204 No Content', async () => {
    const { api } = await import('../api');
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      status: 204,
    });

    const result = await api.auth.logout();

    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/auth/logout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: undefined,
    });
    expect(result).toEqual({});
  });

  it('should throw an error if response is not ok', async () => {
    const { api } = await import('../api');
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Bad request' }),
    });

    await expect(api.auth.me()).rejects.toThrow('Bad request');
  });

  it('should throw a fallback error if response is not ok and json parsing fails', async () => {
    const { api } = await import('../api');
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => Promise.reject(new Error('Parse error')),
    });

    await expect(api.auth.me()).rejects.toThrow('Request failed');
  });

  it('should throw a fallback error if error response json has no detail', async () => {
    const { api } = await import('../api');
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({}),
    });

    await expect(api.auth.me()).rejects.toThrow('Request failed');
  });
});
