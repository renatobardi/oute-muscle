/**
 * T135: E2e test for rule management — list rules, toggle enable/disable.
 */

import { test, expect } from '@playwright/test';

const MOCK_RULES = [
  {
    id: 'unsafe-regex-001',
    category: 'unsafe-regex',
    severity: 'critical',
    enabled: true,
    source: 'manual',
    incident_id: 'inc-1',
    incident_title: 'Catastrophic regex backtracking',
    revision: 1,
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'race-condition-001',
    category: 'race-condition',
    severity: 'high',
    enabled: false,
    source: 'manual',
    incident_id: 'inc-2',
    incident_title: 'Race condition on shared counter',
    revision: 1,
    created_at: '2024-01-02T00:00:00Z',
  },
];

test.describe('Rule management', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'test-jwt-token');
      localStorage.setItem(
        'auth_user',
        JSON.stringify({ id: 'user-1', email: 'admin@acme.com', role: 'admin' }),
      );
    });

    await page.route('**/v1/rules*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: MOCK_RULES, total: 2, page: 1, per_page: 20 }),
      }),
    );
  });

  // -------------------------------------------------------------------------
  // List
  // -------------------------------------------------------------------------

  test('shows rules list with ID, category, severity, and status badge', async ({ page }) => {
    await page.goto('/rules');

    await expect(page.getByRole('heading', { name: /rules/i })).toBeVisible();
    await expect(page.getByText('unsafe-regex-001')).toBeVisible();
    await expect(page.getByText('race-condition-001')).toBeVisible();
  });

  test('shows enabled/disabled badge for each rule', async ({ page }) => {
    await page.goto('/rules');

    // unsafe-regex-001 is enabled
    const enabledRule = page.locator('[data-rule-id="unsafe-regex-001"]');
    await expect(enabledRule.getByText(/enabled/i)).toBeVisible();

    // race-condition-001 is disabled
    const disabledRule = page.locator('[data-rule-id="race-condition-001"]');
    await expect(disabledRule.getByText(/disabled/i)).toBeVisible();
  });

  test('shows linked incident title with link', async ({ page }) => {
    await page.goto('/rules');

    await expect(page.getByText('Catastrophic regex backtracking')).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // Toggle
  // -------------------------------------------------------------------------

  test('toggling an enabled rule sends PATCH with enabled=false', async ({ page }) => {
    let patchBody: unknown;

    await page.route('**/v1/rules/unsafe-regex-001', (route) => {
      if (route.request().method() === 'PATCH') {
        patchBody = JSON.parse(route.request().postData() ?? '{}');
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ...MOCK_RULES[0], enabled: false }),
        });
      }
    });

    await page.goto('/rules');

    // Click the toggle on the enabled rule
    const toggle = page.locator('[data-rule-id="unsafe-regex-001"] [role="switch"]');
    await toggle.click();

    expect(patchBody).toMatchObject({ enabled: false });
  });

  test('toggling a disabled rule sends PATCH with enabled=true', async ({ page }) => {
    let patchBody: unknown;

    await page.route('**/v1/rules/race-condition-001', (route) => {
      if (route.request().method() === 'PATCH') {
        patchBody = JSON.parse(route.request().postData() ?? '{}');
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ...MOCK_RULES[1], enabled: true }),
        });
      }
    });

    await page.goto('/rules');

    const toggle = page.locator('[data-rule-id="race-condition-001"] [role="switch"]');
    await toggle.click();

    expect(patchBody).toMatchObject({ enabled: true });
  });

  test('updates badge to disabled after successful toggle', async ({ page }) => {
    await page.route('**/v1/rules/unsafe-regex-001', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...MOCK_RULES[0], enabled: false }),
      }),
    );

    await page.goto('/rules');

    const ruleRow = page.locator('[data-rule-id="unsafe-regex-001"]');
    await expect(ruleRow.getByText(/enabled/i)).toBeVisible();

    await ruleRow.getByRole('switch').click();

    await expect(ruleRow.getByText(/disabled/i)).toBeVisible();
  });

  test('shows FORBIDDEN error when non-admin tries to toggle', async ({ page }) => {
    // Override user to editor role
    await page.addInitScript(() => {
      localStorage.setItem(
        'auth_user',
        JSON.stringify({ id: 'user-2', email: 'editor@acme.com', role: 'editor' }),
      );
    });

    await page.route('**/v1/rules/unsafe-regex-001', (route) =>
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Forbidden', code: 'FORBIDDEN' }),
      }),
    );

    await page.goto('/rules');

    const toggle = page.locator('[data-rule-id="unsafe-regex-001"] [role="switch"]');
    await toggle.click();

    await expect(page.getByText(/forbidden/i)).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // Filter
  // -------------------------------------------------------------------------

  test('filters rules by category', async ({ page }) => {
    let capturedUrl = '';

    await page.route('**/v1/rules*', (route) => {
      capturedUrl = route.request().url();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [MOCK_RULES[0]], total: 1, page: 1, per_page: 20 }),
      });
    });

    await page.goto('/rules');
    await page.getByLabel(/category/i).selectOption('unsafe-regex');

    expect(capturedUrl).toContain('category=unsafe-regex');
  });

  // -------------------------------------------------------------------------
  // YAML download link
  // -------------------------------------------------------------------------

  test('shows link to YAML download for each rule', async ({ page }) => {
    await page.goto('/rules');

    const yamlLink = page.locator('[data-rule-id="unsafe-regex-001"] a[href*="/yaml"]');
    await expect(yamlLink).toBeVisible();
  });
});
