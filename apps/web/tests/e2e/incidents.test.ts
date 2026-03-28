/**
 * T134: E2e test for incident CRUD flow.
 * Flow: list → create → edit → soft-delete.
 * Requires a running dev server (baseURL configured in playwright.config.ts).
 */

import { test, expect } from '@playwright/test';

test.describe('Incident CRUD flow', () => {
  test.beforeEach(async ({ page }) => {
    // Set auth token in localStorage so the auth guard passes
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'test-jwt-token');
      localStorage.setItem(
        'auth_user',
        JSON.stringify({ id: 'user-1', email: 'admin@acme.com', role: 'admin' })
      );
    });
  });

  // -------------------------------------------------------------------------
  // List
  // -------------------------------------------------------------------------

  test('shows incident list page with search bar', async ({ page }) => {
    await page.goto('/incidents');

    await expect(page.getByRole('heading', { name: /incidents/i })).toBeVisible();
    await expect(page.getByRole('searchbox')).toBeVisible();
    await expect(page.getByRole('button', { name: /new incident/i })).toBeVisible();
  });

  test('displays incidents returned from API', async ({ page }) => {
    await page.route('**/v1/incidents*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'inc-1',
              title: 'Catastrophic regex backtracking',
              category: 'unsafe-regex',
              severity: 'critical',
              anti_pattern: '(?:(?:\\")+)+',
              remediation: 'Use RE2',
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
        }),
      })
    );

    await page.goto('/incidents');

    await expect(page.getByText('Catastrophic regex backtracking')).toBeVisible();
    await expect(page.getByText('unsafe-regex')).toBeVisible();
    await expect(page.getByText('critical')).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // Create
  // -------------------------------------------------------------------------

  test('opens create form and submits new incident', async ({ page }) => {
    await page.route('**/v1/incidents', (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [], total: 0, page: 1, per_page: 20 }),
        });
      }
      // POST
      return route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'inc-new',
          title: 'New SQL injection incident',
          category: 'injection',
          severity: 'critical',
          anti_pattern: 'f"SELECT * FROM users WHERE id = {user_id}"',
          remediation: 'Use parameterized queries',
          affected_languages: ['python'],
          static_rule_possible: true,
          version: 1,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        }),
      });
    });

    await page.goto('/incidents');
    await page.getByRole('button', { name: /new incident/i }).click();

    // Fill form
    await page.getByLabel(/title/i).fill('New SQL injection incident');
    await page.getByLabel(/category/i).selectOption('injection');
    await page.getByLabel(/severity/i).selectOption('critical');
    await page.getByLabel(/anti.pattern/i).fill('f"SELECT * FROM users WHERE id = {user_id}"');
    await page.getByLabel(/remediation/i).fill('Use parameterized queries');

    await page.getByRole('button', { name: /save/i }).click();

    // Should show success or redirect to the new incident
    await expect(page.getByText('New SQL injection incident')).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // Edit
  // -------------------------------------------------------------------------

  test('edits existing incident with optimistic locking', async ({ page }) => {
    const incident = {
      id: 'inc-1',
      title: 'Old title',
      category: 'unsafe-regex',
      severity: 'high',
      anti_pattern: 'bad pattern',
      remediation: 'fix it',
      affected_languages: ['python'],
      static_rule_possible: false,
      version: 2,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    };

    await page.route('**/v1/incidents/inc-1', (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(incident),
        });
      }
      // PUT
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...incident, title: 'Updated title', version: 3 }),
      });
    });

    await page.goto('/incidents/inc-1');

    await expect(page.getByDisplayValue('Old title')).toBeVisible();
    await page.getByLabel(/title/i).fill('Updated title');
    await page.getByRole('button', { name: /save/i }).click();

    await expect(page.getByText('Updated title')).toBeVisible();
  });

  test('shows conflict error when optimistic locking fails', async ({ page }) => {
    await page.route('**/v1/incidents/inc-1', (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'inc-1',
            title: 'Old title',
            category: 'unsafe-regex',
            severity: 'high',
            anti_pattern: 'bad',
            remediation: 'fix',
            affected_languages: [],
            static_rule_possible: false,
            version: 2,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          }),
        });
      }
      return route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Conflict — incident modified by another user. Reload and retry.',
          code: 'CONFLICT',
          current_version: 5,
        }),
      });
    });

    await page.goto('/incidents/inc-1');
    await page.getByLabel(/title/i).fill('My change');
    await page.getByRole('button', { name: /save/i }).click();

    await expect(page.getByText(/conflict/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /reload/i })).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // Delete
  // -------------------------------------------------------------------------

  test('soft-deletes an incident and redirects to list', async ({ page }) => {
    await page.route('**/v1/incidents/inc-1', (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'inc-1',
            title: 'To be deleted',
            category: 'injection',
            severity: 'high',
            anti_pattern: 'x',
            remediation: 'y',
            affected_languages: [],
            static_rule_possible: false,
            version: 1,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          }),
        });
      }
      return route.fulfill({ status: 204, body: '' });
    });

    await page.route('**/v1/incidents*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], total: 0, page: 1, per_page: 20 }),
      })
    );

    await page.goto('/incidents/inc-1');
    await page.getByRole('button', { name: /delete/i }).click();

    // Confirmation dialog
    await page.getByRole('button', { name: /confirm/i }).click();

    // Redirected back to list
    await expect(page).toHaveURL('/incidents');
  });

  test('shows error when deleting incident with active linked rule', async ({ page }) => {
    await page.route('**/v1/incidents/inc-1', (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'inc-1',
            title: 'Linked incident',
            category: 'unsafe-regex',
            severity: 'critical',
            anti_pattern: 'x',
            remediation: 'y',
            affected_languages: [],
            static_rule_possible: true,
            version: 1,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          }),
        });
      }
      return route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Cannot delete — incident has active linked rule',
          code: 'CONFLICT',
          rule_id: 'unsafe-regex-001',
        }),
      });
    });

    await page.goto('/incidents/inc-1');
    await page.getByRole('button', { name: /delete/i }).click();
    await page.getByRole('button', { name: /confirm/i }).click();

    await expect(page.getByText(/active linked rule/i)).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // Ingest from URL
  // -------------------------------------------------------------------------

  test('ingest-from-URL page shows draft for review', async ({ page }) => {
    await page.route('**/v1/incidents/ingest-url', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          draft: {
            title: 'Cloudflare regex outage',
            category: 'unsafe-regex',
            severity: 'critical',
            anti_pattern: '(?:(?:\\")+)+',
            remediation: 'Use RE2',
            affected_languages: ['python'],
            static_rule_possible: true,
            source_url:
              'https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019',
            organization: 'Cloudflare',
          },
        }),
      })
    );

    await page.goto('/incidents/ingest');

    await page
      .getByLabel(/url/i)
      .fill('https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019');
    await page.getByRole('button', { name: /extract/i }).click();

    await expect(page.getByText('Cloudflare regex outage')).toBeVisible();
    await expect(page.getByRole('button', { name: /confirm/i })).toBeVisible();
  });
});
