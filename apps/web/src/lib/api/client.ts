/**
 * T139: Typed API client library.
 * Covers: auth token injection, error parsing, all REST endpoints from api-rest.md.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Severity = 'critical' | 'high' | 'medium' | 'low';
export type Category =
  | 'unsafe-regex'
  | 'race-condition'
  | 'missing-error-handling'
  | 'injection'
  | 'resource-exhaustion'
  | 'missing-safety-check'
  | 'deployment-error'
  | 'data-consistency'
  | 'unsafe-api-usage'
  | 'cascading-failure';

export type Role = 'admin' | 'editor' | 'viewer';
export type Plan = 'free' | 'team' | 'enterprise';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type RuleSource = 'manual' | 'synthesized';

export interface Incident {
  id: string;
  title: string;
  category: Category;
  severity: Severity;
  anti_pattern: string;
  remediation: string;
  affected_languages: string[];
  code_example?: string;
  source_url?: string;
  organization?: string;
  static_rule_possible: boolean;
  tags?: string[];
  version: number;
  linked_rule_id?: string;
  created_at: string;
  updated_at: string;
  deleted_at?: string;
}

export interface IncidentDraft {
  title: string;
  category: Category;
  severity: Severity;
  anti_pattern: string;
  remediation: string;
  affected_languages: string[];
  code_example?: string;
  source_url?: string;
  organization?: string | null;
  static_rule_possible: boolean;
  tags?: string[];
}

export interface Rule {
  id: string;
  category: Category;
  severity: Severity;
  enabled: boolean;
  source: RuleSource;
  incident_id: string;
  incident_title?: string;
  revision: number;
  approved_by?: string;
  created_at: string;
}

export interface Finding {
  id: string;
  rule_id: string;
  incident_id: string;
  incident_url?: string;
  file_path: string;
  start_line: number;
  end_line: number;
  severity: Severity;
  category: Category;
  message: string;
  remediation: string;
  false_positive: boolean;
  false_positive_count: number;
}

export interface Advisory {
  id: string;
  incident_id: string;
  incident_title: string;
  confidence: number;
  severity: Severity;
  message: string;
  file_path?: string;
  start_line?: number;
}

export interface Scan {
  id: string;
  repository: string;
  commit_sha: string;
  pr_number?: number;
  risk_level: RiskLevel;
  findings_count: number;
  advisories_count?: number;
  duration_ms: number;
  created_at: string;
  findings?: Finding[];
  advisories?: Advisory[];
}

export interface TenantUser {
  id: string;
  email: string;
  role: Role;
  joined_at: string;
}

export interface Tenant {
  id: string;
  name: string;
  plan: Plan;
  contributor_count: number;
  repo_count: number;
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  entity_type: string;
  entity_id: string;
  action: 'create' | 'update' | 'delete';
  actor_id: string;
  actor_email: string;
  before?: Record<string, unknown>;
  after?: Record<string, unknown>;
  created_at: string;
}

export interface SynthesisCandidate {
  id: string;
  anti_pattern_hash: string;
  advisory_count: number;
  status: 'pending' | 'approved' | 'rejected' | 'failed' | 'archived';
  failure_count: number;
  failure_reason?: string;
  generated_rule_yaml?: string;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// ---------------------------------------------------------------------------
// Client implementation
// ---------------------------------------------------------------------------

export interface ApiClientOptions {
  baseUrl: string;
  /** Provide a custom fetch (useful for testing). Defaults to globalThis.fetch. */
  fetch?: typeof fetch;
  token?: string;
}

type FetchFn = typeof fetch;

export class ApiClient {
  private _token: string | null;
  private readonly _fetch: FetchFn;
  private readonly _baseUrl: string;

  constructor(options: ApiClientOptions) {
    this._baseUrl = options.baseUrl.replace(/\/$/, '');
    this._fetch = options.fetch ?? globalThis.fetch;
    this._token = options.token ?? null;
  }

  setToken(token: string | null): void {
    this._token = token;
  }

  // -------------------------------------------------------------------------
  // Core request helper
  // -------------------------------------------------------------------------

  private async request<T>(
    method: string,
    path: string,
    options: {
      params?: Record<string, string | number | boolean | undefined>;
      body?: unknown;
      accept?: string;
    } = {}
  ): Promise<T> {
    const url = new URL(`${this._baseUrl}${path}`);
    if (options.params) {
      for (const [key, value] of Object.entries(options.params)) {
        if (value !== undefined && value !== null) {
          url.searchParams.set(key, String(value));
        }
      }
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (options.accept) {
      headers['Accept'] = options.accept;
    }
    if (this._token) {
      headers['Authorization'] = `Bearer ${this._token}`;
    }

    const response = await this._fetch(url.toString(), {
      method,
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });

    // 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    const data = await response.json();

    if (!response.ok) {
      throw new ApiError(
        response.status,
        data.code ?? 'UNKNOWN',
        data.error ?? `HTTP ${response.status}`,
        data.details
      );
    }

    return data as T;
  }

  // -------------------------------------------------------------------------
  // Incidents namespace
  // -------------------------------------------------------------------------

  readonly incidents = {
    list: (params?: {
      q?: string;
      semantic?: boolean;
      category?: string;
      severity?: string;
      page?: number;
      per_page?: number;
    }): Promise<PaginatedResponse<Incident>> => this.request('GET', '/incidents', { params }),

    get: (id: string): Promise<Incident> => this.request('GET', `/incidents/${id}`),

    create: (payload: Omit<IncidentDraft, never>): Promise<Incident> =>
      this.request('POST', '/incidents', { body: payload }),

    update: (
      id: string,
      payload: Partial<IncidentDraft> & { version: number }
    ): Promise<Incident> => this.request('PUT', `/incidents/${id}`, { body: payload }),

    delete: (id: string): Promise<void> => this.request('DELETE', `/incidents/${id}`),

    ingestUrl: (url: string): Promise<{ draft: IncidentDraft }> =>
      this.request('POST', '/incidents/ingest-url', { body: { url } }),
  };

  // -------------------------------------------------------------------------
  // Rules namespace
  // -------------------------------------------------------------------------

  readonly rules = {
    list: (params?: {
      category?: string;
      enabled?: boolean;
      source?: RuleSource;
      page?: number;
      per_page?: number;
    }): Promise<PaginatedResponse<Rule>> => this.request('GET', '/rules', { params }),

    get: (id: string): Promise<Rule> => this.request('GET', `/rules/${id}`),

    toggle: (id: string, enabled: boolean): Promise<Rule> =>
      this.request('PATCH', `/rules/${id}`, { body: { enabled } }),
  };

  // -------------------------------------------------------------------------
  // Scans namespace
  // -------------------------------------------------------------------------

  readonly scans = {
    list: (params?: {
      repository?: string;
      status?: string;
      from?: string;
      to?: string;
      page?: number;
      per_page?: number;
    }): Promise<PaginatedResponse<Scan>> => this.request('GET', '/scans', { params }),

    get: (id: string): Promise<Scan> => this.request('GET', `/scans/${id}`),

    trigger: (payload: {
      diff: string;
      repository: string;
      commit_sha: string;
      pr_number?: number;
    }): Promise<Scan> => this.request('POST', '/scans', { body: payload }),
  };

  // -------------------------------------------------------------------------
  // Findings namespace
  // -------------------------------------------------------------------------

  readonly findings = {
    reportFalsePositive: (id: string): Promise<void> =>
      this.request('POST', `/findings/${id}/false-positive`),
  };

  // -------------------------------------------------------------------------
  // Tenants namespace
  // -------------------------------------------------------------------------

  readonly tenants = {
    me: (): Promise<Tenant> => this.request('GET', '/tenants/me'),

    users: (): Promise<TenantUser[]> => this.request('GET', '/tenants/me/users'),

    invite: (payload: { email: string; role: Role }): Promise<{ message: string }> =>
      this.request('POST', '/tenants/me/users/invite', { body: payload }),

    updateUserRole: (userId: string, role: Role): Promise<TenantUser> =>
      this.request('PATCH', `/tenants/me/users/${userId}`, { body: { role } }),
  };

  // -------------------------------------------------------------------------
  // Audit log namespace (Enterprise)
  // -------------------------------------------------------------------------

  readonly auditLog = {
    list: (params?: {
      entity_type?: string;
      action?: string;
      from?: string;
      to?: string;
      page?: number;
      per_page?: number;
    }): Promise<PaginatedResponse<AuditLogEntry>> => this.request('GET', '/audit-log', { params }),
  };

  // -------------------------------------------------------------------------
  // Synthesis candidates namespace (Enterprise)
  // -------------------------------------------------------------------------

  readonly synthesis = {
    listCandidates: (params?: {
      page?: number;
      per_page?: number;
    }): Promise<PaginatedResponse<SynthesisCandidate>> =>
      this.request('GET', '/synthesis/candidates', { params }),

    approve: (id: string): Promise<{ rule_id: string }> =>
      this.request('POST', `/synthesis/candidates/${id}/approve`),

    reject: (id: string): Promise<void> =>
      this.request('POST', `/synthesis/candidates/${id}/reject`),
  };
}
