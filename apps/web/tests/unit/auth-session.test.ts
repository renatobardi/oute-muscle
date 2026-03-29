/**
 * T013: Unit tests for session exchange endpoint.
 *
 * Mocks firebase-admin to test POST (valid/invalid token) and DELETE.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// ---------------------------------------------------------------------------
// Mocks — must be declared before importing the module under test
// ---------------------------------------------------------------------------

const mockVerifyIdToken = vi.fn();
const mockCreateSessionCookie = vi.fn();

vi.mock('$lib/server/firebase-admin', () => ({
  getAdminAuth: () => ({
    verifyIdToken: mockVerifyIdToken,
    createSessionCookie: mockCreateSessionCookie,
  }),
}));

vi.mock('$env/dynamic/private', () => ({
  env: {
    ADMIN_EMAILS: 'admin@oute.pro',
    FIREBASE_PROJECT_ID: 'oute-test',
    FIREBASE_CLIENT_EMAIL: '',
    FIREBASE_PRIVATE_KEY: '',
  },
}));

// ---------------------------------------------------------------------------
// Import the handler after mocks are set up
// ---------------------------------------------------------------------------

import { POST, DELETE } from '../../src/routes/api/auth/session/+server';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeRequest(body: unknown): Request {
  return new Request('http://localhost/api/auth/session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

function makeCookies() {
  const store = new Map<string, string>();
  return {
    get: (name: string) => store.get(name),
    set: (name: string, value: string, _opts?: unknown) => {
      store.set(name, value);
    },
    delete: (name: string, _opts?: unknown) => {
      store.delete(name);
    },
    serialize: () => '',
    getAll: () => [],
    _store: store,
  };
}

function makeEvent(request: Request, cookies = makeCookies()) {
  return {
    request,
    cookies,
    url: new URL(request.url),
    params: {},
    locals: {},
    platform: undefined,
    route: { id: '/api/auth/session' },
    isDataRequest: false,
    isSubRequest: false,
    getClientAddress: () => '127.0.0.1',
    setHeaders: vi.fn(),
    fetch: globalThis.fetch,
  } as unknown as Parameters<typeof POST>[0];
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('POST /api/auth/session', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns 200 with user data and sets cookie for valid idToken', async () => {
    mockVerifyIdToken.mockResolvedValue({
      uid: 'firebase-uid-1',
      email: 'user@example.com',
      name: 'Test User',
    });
    mockCreateSessionCookie.mockResolvedValue('session-cookie-value');

    const cookies = makeCookies();
    const event = makeEvent(makeRequest({ idToken: 'valid-id-token' }), cookies);
    const response = await POST(event);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.user).toBeDefined();
    expect(data.user.firebaseUid).toBe('firebase-uid-1');
    expect(data.user.email).toBe('user@example.com');
    expect(data.user.role).toBe('viewer');
    expect(cookies._store.get('__session')).toBe('session-cookie-value');
  });

  it('returns 401 for invalid idToken', async () => {
    mockVerifyIdToken.mockRejectedValue(new Error('Token is invalid'));

    const event = makeEvent(makeRequest({ idToken: 'invalid-token' }));
    const response = await POST(event);
    const data = await response.json();

    expect(response.status).toBe(401);
    expect(data.error).toBe('Invalid or expired token');
  });

  it('returns 400 when idToken is missing', async () => {
    const event = makeEvent(makeRequest({}));
    const response = await POST(event);
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.error).toBe('Missing idToken');
  });
});

describe('DELETE /api/auth/session', () => {
  it('clears cookie and returns logged_out status', async () => {
    const cookies = makeCookies();
    cookies.set('__session', 'some-cookie');

    const request = new Request('http://localhost/api/auth/session', { method: 'DELETE' });
    const event = makeEvent(request, cookies);
    const response = await DELETE(event);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.status).toBe('logged_out');
  });
});
