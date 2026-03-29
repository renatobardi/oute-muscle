/**
 * T133: Unit tests for the typed API client.
 * Tests: auth token injection, error parsing, pagination, content negotiation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  ApiClient,
  ApiError,
  type Incident,
  type PaginatedResponse,
  type Rule,
  type Scan,
  type Tenant,
} from '../../src/lib/api/client';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mockFetch(status: number, body: unknown, headers: Record<string, string> = {}) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    headers: {
      get: (key: string) => headers[key.toLowerCase()] ?? null,
    },
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ApiClient', () => {
  let client: ApiClient;
  let fetchSpy: ReturnType<typeof mockFetch>;

  beforeEach(() => {
    fetchSpy = mockFetch(200, {});
    client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // -------------------------------------------------------------------------
  // Auth token injection
  // -------------------------------------------------------------------------

  describe('auth token injection', () => {
    it('sends Authorization header when token is set', async () => {
      client.setToken('my-jwt-token');
      fetchSpy = mockFetch(200, { items: [], total: 0, page: 1, per_page: 20 });
      client = new ApiClient({
        baseUrl: 'https://muscle.oute.pro/api/v1',
        fetch: fetchSpy,
        token: 'my-jwt-token',
      });

      await client.incidents.list();

      const [_url, options] = fetchSpy.mock.calls[0];
      expect((options as RequestInit).headers).toMatchObject({
        Authorization: 'Bearer my-jwt-token',
      });
    });

    it('omits Authorization header when no token is set', async () => {
      fetchSpy = mockFetch(200, { items: [], total: 0, page: 1, per_page: 20 });
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });

      await client.incidents.list();

      const [_url, options] = fetchSpy.mock.calls[0];
      expect(
        (options as RequestInit & { headers: Record<string, string> }).headers?.Authorization
      ).toBeUndefined();
    });

    it('updates token dynamically via setToken', async () => {
      fetchSpy = mockFetch(200, { items: [], total: 0, page: 1, per_page: 20 });
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });
      client.setToken('updated-token');

      await client.incidents.list();

      const [_url, options] = fetchSpy.mock.calls[0];
      expect((options as RequestInit).headers).toMatchObject({
        Authorization: 'Bearer updated-token',
      });
    });
  });

  // -------------------------------------------------------------------------
  // Error parsing
  // -------------------------------------------------------------------------

  describe('error parsing', () => {
    it('throws ApiError with code and message on 4xx', async () => {
      fetchSpy = mockFetch(409, {
        error: 'Conflict — incident modified by another user',
        code: 'CONFLICT',
      });
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });

      await expect(client.incidents.get('abc')).rejects.toThrow(ApiError);

      try {
        await client.incidents.get('abc');
      } catch (e) {
        const err = e as ApiError;
        expect(err.status).toBe(409);
        expect(err.code).toBe('CONFLICT');
        expect(err.message).toContain('Conflict');
      }
    });

    it('throws ApiError on 401 UNAUTHORIZED', async () => {
      fetchSpy = mockFetch(401, { error: 'Unauthorized', code: 'UNAUTHORIZED' });
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });

      await expect(client.incidents.list()).rejects.toThrow(ApiError);
    });

    it('throws ApiError on 404 NOT_FOUND', async () => {
      fetchSpy = mockFetch(404, { error: 'Incident not found', code: 'NOT_FOUND' });
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });

      await expect(client.incidents.get('nonexistent')).rejects.toMatchObject({
        status: 404,
        code: 'NOT_FOUND',
      });
    });

    it('throws ApiError with RATE_LIMITED code on 429', async () => {
      fetchSpy = mockFetch(429, { error: 'Rate limit exceeded', code: 'RATE_LIMITED' });
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });

      await expect(client.incidents.list()).rejects.toMatchObject({ code: 'RATE_LIMITED' });
    });
  });

  // -------------------------------------------------------------------------
  // Incidents
  // -------------------------------------------------------------------------

  describe('incidents.list', () => {
    it('returns paginated incident list', async () => {
      const payload: PaginatedResponse<Incident> = {
        items: [
          {
            id: 'inc-1',
            title: 'Catastrophic regex backtracking',
            category: 'unsafe-regex',
            severity: 'critical',
            anti_pattern: 'nested quantifiers',
            remediation: 'use RE2',
            affected_languages: ['python'],
            static_rule_possible: true,
            version: 1,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        per_page: 20,
      };
      fetchSpy = mockFetch(200, payload);
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });

      const result = await client.incidents.list();

      expect(result.items).toHaveLength(1);
      expect(result.items[0].id).toBe('inc-1');
      expect(result.total).toBe(1);
    });

    it('forwards query params (q, semantic, category, page)', async () => {
      fetchSpy = mockFetch(200, { items: [], total: 0, page: 2, per_page: 20 });
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });

      await client.incidents.list({
        q: 'regex',
        semantic: true,
        category: 'unsafe-regex',
        page: 2,
      });

      const [url] = fetchSpy.mock.calls[0];
      expect(url).toContain('q=regex');
      expect(url).toContain('semantic=true');
      expect(url).toContain('category=unsafe-regex');
      expect(url).toContain('page=2');
    });
  });

  describe('incidents.get', () => {
    it('fetches a single incident by ID', async () => {
      const incident: Incident = {
        id: 'inc-1',
        title: 'Test',
        category: 'race-condition',
        severity: 'high',
        anti_pattern: 'shared state',
        remediation: 'use locks',
        affected_languages: ['go'],
        static_rule_possible: false,
        version: 3,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };
      fetchSpy = mockFetch(200, incident);
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });

      const result = await client.incidents.get('inc-1');

      expect(result.id).toBe('inc-1');
      expect(result.version).toBe(3);
    });
  });

  describe('incidents.create', () => {
    it('sends POST with incident payload and returns 201 body', async () => {
      const created: Incident = {
        id: 'inc-new',
        title: 'New incident',
        category: 'injection',
        severity: 'critical',
        anti_pattern: 'raw SQL',
        remediation: 'use parameterized queries',
        affected_languages: ['python'],
        static_rule_possible: true,
        version: 1,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };
      fetchSpy = mockFetch(201, created);
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });

      const result = await client.incidents.create({
        title: 'New incident',
        category: 'injection',
        severity: 'critical',
        anti_pattern: 'raw SQL',
        remediation: 'use parameterized queries',
        affected_languages: ['python'],
        static_rule_possible: true,
      });

      expect(result.id).toBe('inc-new');
      const [url, options] = fetchSpy.mock.calls[0];
      expect(url).toContain('/incidents');
      expect((options as RequestInit).method).toBe('POST');
    });
  });

  describe('incidents.update', () => {
    it('sends PUT with version for optimistic locking', async () => {
      const updated: Incident = {
        id: 'inc-1',
        title: 'Updated',
        category: 'unsafe-regex',
        severity: 'high',
        anti_pattern: 'updated',
        remediation: 'updated',
        affected_languages: [],
        static_rule_possible: false,
        version: 4,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-02T00:00:00Z',
      };
      fetchSpy = mockFetch(200, updated);
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });

      await client.incidents.update('inc-1', { title: 'Updated', version: 3 });

      const [url, options] = fetchSpy.mock.calls[0];
      expect(url).toContain('/incidents/inc-1');
      expect((options as RequestInit).method).toBe('PUT');
      const body = JSON.parse((options as RequestInit).body as string);
      expect(body.version).toBe(3);
    });
  });

  describe('incidents.delete', () => {
    it('sends DELETE request', async () => {
      fetchSpy = mockFetch(204, null);
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });

      await client.incidents.delete('inc-1');

      const [url, options] = fetchSpy.mock.calls[0];
      expect(url).toContain('/incidents/inc-1');
      expect((options as RequestInit).method).toBe('DELETE');
    });
  });

  describe('incidents.ingestUrl', () => {
    it('sends POST /incidents/ingest-url and returns draft', async () => {
      const draft = {
        draft: {
          title: 'Cloudflare outage',
          category: 'unsafe-regex',
          severity: 'critical',
        },
      };
      fetchSpy = mockFetch(200, draft);
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });

      const result = await client.incidents.ingestUrl('https://example.com/post-mortem');

      expect(result.draft.title).toBe('Cloudflare outage');
    });
  });

  // -------------------------------------------------------------------------
  // Rules
  // -------------------------------------------------------------------------

  describe('rules.list', () => {
    it('returns paginated rule list', async () => {
      const payload: PaginatedResponse<Rule> = {
        items: [
          {
            id: 'unsafe-regex-001',
            category: 'unsafe-regex',
            severity: 'critical',
            enabled: true,
            source: 'manual',
            incident_id: 'inc-1',
            revision: 1,
            created_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        per_page: 20,
      };
      fetchSpy = mockFetch(200, payload);
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });

      const result = await client.rules.list();

      expect(result.items[0].id).toBe('unsafe-regex-001');
    });
  });

  describe('rules.toggle', () => {
    it('sends PATCH /rules/:id with enabled field', async () => {
      fetchSpy = mockFetch(200, { id: 'unsafe-regex-001', enabled: false });
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });

      await client.rules.toggle('unsafe-regex-001', false);

      const [url, options] = fetchSpy.mock.calls[0];
      expect(url).toContain('/rules/unsafe-regex-001');
      expect((options as RequestInit).method).toBe('PATCH');
      const body = JSON.parse((options as RequestInit).body as string);
      expect(body.enabled).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // Scans
  // -------------------------------------------------------------------------

  describe('scans.list', () => {
    it('returns paginated scan list', async () => {
      const payload: PaginatedResponse<Scan> = {
        items: [
          {
            id: 'scan-1',
            repository: 'org/repo',
            commit_sha: 'abc123',
            risk_level: 'high',
            findings_count: 3,
            duration_ms: 1200,
            created_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        per_page: 20,
      };
      fetchSpy = mockFetch(200, payload);
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });

      const result = await client.scans.list();

      expect(result.items[0].id).toBe('scan-1');
    });
  });

  // -------------------------------------------------------------------------
  // Tenants
  // -------------------------------------------------------------------------

  describe('tenants.me', () => {
    it('fetches current tenant profile', async () => {
      const tenant: Tenant = {
        id: 'tenant-1',
        name: 'Acme Corp',
        plan: 'team',
        contributor_count: 5,
        repo_count: 3,
        created_at: '2024-01-01T00:00:00Z',
      };
      fetchSpy = mockFetch(200, tenant);
      client = new ApiClient({ baseUrl: 'https://muscle.oute.pro/api/v1', fetch: fetchSpy });

      const result = await client.tenants.me();

      expect(result.id).toBe('tenant-1');
      expect(result.plan).toBe('team');
    });
  });
});
