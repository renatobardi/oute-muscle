/**
 * T044: E2e test for admin user management.
 * Tests: search user, change role.
 */

import { test, expect } from '@playwright/test';

const mockUsers = {
  items: [
    {
      id: 'user-1',
      email: 'alice@acme.com',
      display_name: 'Alice Smith',
      tenant_id: 'tenant-1',
      tenant_name: 'Acme Corp',
      role: 'editor',
      is_active: true,
      email_verified: true,
      last_login: '2026-03-28T10:00:00Z',
      created_at: '2026-01-15T00:00:00Z',
    },
    {
      id: 'user-2',
      email: 'bob@acme.com',
      display_name: 'Bob Jones',
      tenant_id: 'tenant-1',
      tenant_name: 'Acme Corp',
      role: 'viewer',
      is_active: true,
      email_verified: true,
      last_login: '2026-03-27T14:30:00Z',
      created_at: '2026-02-01T00:00:00Z',
    },
  ],
  total: 2,
  page: 1,
  per_page: 50,
};

test.describe('Admin user management', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'test-jwt-token');
      localStorage.setItem(
        'auth_user',
        JSON.stringify({ id: 'admin-1', email: 'admin@acme.com', role: 'admin' })
      );
    });
  });

  test('displays user list with search functionality', async ({ page }) => {
    await page.route('**/v1/admin/users*', (route) => {
      const url = new URL(route.request().url());
      const q = url.searchParams.get('q');

      if (q === 'alice') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [mockUsers.items[0]],
            total: 1,
            page: 1,
            per_page: 50,
          }),
        });
      }

      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUsers),
      });
    });

    await page.goto('/admin/users');

    // Should display all users
    await expect(page.getByText('alice@acme.com')).toBeVisible();
    await expect(page.getByText('bob@acme.com')).toBeVisible();

    // Search for alice
    await page.getByPlaceholder(/search/i).fill('alice');

    // Wait for debounce and filtered result
    await expect(page.getByText('alice@acme.com')).toBeVisible();
    await expect(page.getByText('bob@acme.com')).not.toBeVisible();
  });

  test('can change user role via dropdown', async ({ page }) => {
    let roleChanged = false;

    await page.route('**/v1/admin/users*', (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockUsers),
        });
      }
      return route.continue();
    });

    await page.route('**/v1/admin/users/user-2/role', (route) => {
      roleChanged = true;
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user-2',
          email: 'bob@acme.com',
          role: 'editor',
          updated_at: '2026-03-29T00:00:00Z',
        }),
      });
    });

    await page.goto('/admin/users');

    // Find the role button for bob's row and click it
    const bobRow = page.getByRole('row').filter({ hasText: 'bob@acme.com' });
    await bobRow.getByRole('button', { name: /role/i }).click();

    // Select 'editor' from the dropdown
    await page.getByRole('button', { name: /editor/i }).click();

    // Verify the API was called
    expect(roleChanged).toBe(true);
  });

  test('shows error state when API fails', async ({ page }) => {
    await page.route('**/v1/admin/users*', (route) =>
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error', code: 'INTERNAL' }),
      })
    );

    await page.goto('/admin/users');

    // Should show error with retry button
    await expect(page.getByText(/unable to load data|internal server error/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /retry/i })).toBeVisible();
  });

  test('can deactivate a user', async ({ page }) => {
    let deactivated = false;

    await page.route('**/v1/admin/users*', (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockUsers),
        });
      }
      return route.continue();
    });

    await page.route('**/v1/admin/users/user-2/deactivate', (route) => {
      deactivated = true;
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user-2',
          email: 'bob@acme.com',
          is_active: false,
          updated_at: '2026-03-29T00:00:00Z',
        }),
      });
    });

    await page.goto('/admin/users');

    const bobRow = page.getByRole('row').filter({ hasText: 'bob@acme.com' });
    await bobRow.getByRole('button', { name: /deactivate/i }).click();

    expect(deactivated).toBe(true);
  });
});
