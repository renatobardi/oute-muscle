/**
 * T043: E2e test for admin access control.
 * Tests: admin user can access /admin, non-admin user gets redirected.
 */

import { test, expect } from '@playwright/test';

test.describe('Admin access control', () => {
  test('admin user can access /admin dashboard', async ({ page }) => {
    // Set auth token and admin user in localStorage
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'test-jwt-token');
      localStorage.setItem(
        'auth_user',
        JSON.stringify({ id: 'user-1', email: 'admin@acme.com', role: 'admin' })
      );
    });

    // Mock the admin metrics endpoint
    await page.route('**/v1/admin/metrics', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          users: { total: 10, active_30d: 5 },
          tenants: { total: 3, active: 2 },
          scans: { total_30d: 100, active_now: 1 },
          findings: { total_30d: 50, by_severity: {} },
          incidents: { total: 20, with_embedding: 15, by_category: {} },
          rules: { active: 8, auto_disabled: 1, synthesis_pending: 2 },
          llm_usage_30d: { flash: 100, pro: 50, claude: 25 },
        }),
      })
    );

    await page.goto('/admin');

    // Should see the admin overview page
    await expect(page.getByRole('heading', { name: /admin overview/i })).toBeVisible();
    await expect(page.getByText('Total Users')).toBeVisible();
  });

  test('non-admin user gets redirected away from /admin', async ({ page }) => {
    // Set auth token with non-admin (viewer) role
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'test-jwt-token');
      localStorage.setItem(
        'auth_user',
        JSON.stringify({ id: 'user-2', email: 'viewer@acme.com', role: 'viewer' })
      );
    });

    await page.goto('/admin');

    // Should be redirected to home (not on /admin)
    await expect(page).not.toHaveURL(/\/admin/);
  });

  test('unauthenticated user cannot access /admin', async ({ page }) => {
    // No auth token set
    await page.goto('/admin');

    // Should redirect to login
    await expect(page).not.toHaveURL(/\/admin/);
  });

  test('admin sidebar navigation links are visible', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'test-jwt-token');
      localStorage.setItem(
        'auth_user',
        JSON.stringify({ id: 'user-1', email: 'admin@acme.com', role: 'admin' })
      );
    });

    await page.route('**/v1/admin/metrics', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          users: { total: 0, active_30d: 0 },
          tenants: { total: 0, active: 0 },
          scans: { total_30d: 0, active_now: 0 },
          findings: { total_30d: 0, by_severity: {} },
          incidents: { total: 0, with_embedding: 0, by_category: {} },
          rules: { active: 0, auto_disabled: 0, synthesis_pending: 0 },
          llm_usage_30d: { flash: 0, pro: 0, claude: 0 },
        }),
      })
    );

    await page.goto('/admin');

    // Verify sidebar navigation links
    await expect(page.getByRole('link', { name: /overview/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /users/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /tenants/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /health/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /incidents/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /rules/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /access control/i })).toBeVisible();
  });
});
