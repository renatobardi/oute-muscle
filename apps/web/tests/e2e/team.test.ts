/**
 * T136: E2e test for team management — invite user, change role, verify access.
 */

import { test, expect } from '@playwright/test';

const MOCK_USERS = [
  { id: 'user-1', email: 'admin@acme.com', role: 'admin', joined_at: '2024-01-01T00:00:00Z' },
  { id: 'user-2', email: 'editor@acme.com', role: 'editor', joined_at: '2024-01-15T00:00:00Z' },
];

test.describe('Team management', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'test-jwt-token');
      localStorage.setItem(
        'auth_user',
        JSON.stringify({ id: 'user-1', email: 'admin@acme.com', role: 'admin' }),
      );
    });

    await page.route('**/v1/tenants/me/users*', (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_USERS),
        });
      }
    });

    await page.route('**/v1/tenants/me*', (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'tenant-1',
            name: 'Acme Corp',
            plan: 'team',
            contributor_count: 2,
            repo_count: 3,
            created_at: '2024-01-01T00:00:00Z',
          }),
        });
      }
    });
  });

  // -------------------------------------------------------------------------
  // List members
  // -------------------------------------------------------------------------

  test('shows team members list with email and role', async ({ page }) => {
    await page.goto('/settings');

    await expect(page.getByText('admin@acme.com')).toBeVisible();
    await expect(page.getByText('editor@acme.com')).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // Invite user
  // -------------------------------------------------------------------------

  test('admin can invite a new user by email', async ({ page }) => {
    let inviteBody: unknown;

    await page.route('**/v1/tenants/me/users/invite', (route) => {
      inviteBody = JSON.parse(route.request().postData() ?? '{}');
      return route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Invitation sent' }),
      });
    });

    await page.goto('/settings');
    await page.getByRole('button', { name: /invite/i }).click();

    await page.getByLabel(/email/i).fill('newmember@acme.com');
    await page.getByLabel(/role/i).selectOption('editor');
    await page.getByRole('button', { name: /send invite/i }).click();

    expect(inviteBody).toMatchObject({ email: 'newmember@acme.com', role: 'editor' });
    await expect(page.getByText(/invitation sent/i)).toBeVisible();
  });

  test('shows error when inviting an email that already exists', async ({ page }) => {
    await page.route('**/v1/tenants/me/users/invite', (route) =>
      route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'User already exists in tenant', code: 'CONFLICT' }),
      }),
    );

    await page.goto('/settings');
    await page.getByRole('button', { name: /invite/i }).click();
    await page.getByLabel(/email/i).fill('admin@acme.com');
    await page.getByLabel(/role/i).selectOption('editor');
    await page.getByRole('button', { name: /send invite/i }).click();

    await expect(page.getByText(/already exists/i)).toBeVisible();
  });

  test('shows error when Free plan contributor limit is reached', async ({ page }) => {
    await page.route('**/v1/tenants/me*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'tenant-1',
          name: 'Acme Corp',
          plan: 'free',
          contributor_count: 5,
          repo_count: 1,
          created_at: '2024-01-01T00:00:00Z',
        }),
      }),
    );

    await page.route('**/v1/tenants/me/users/invite', (route) =>
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Plan limit exceeded: max 5 contributors on Free plan',
          code: 'PLAN_LIMIT_EXCEEDED',
        }),
      }),
    );

    await page.goto('/settings');
    await page.getByRole('button', { name: /invite/i }).click();
    await page.getByLabel(/email/i).fill('extra@acme.com');
    await page.getByLabel(/role/i).selectOption('viewer');
    await page.getByRole('button', { name: /send invite/i }).click();

    await expect(page.getByText(/plan limit/i)).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // Change role
  // -------------------------------------------------------------------------

  test('admin can change a member role', async ({ page }) => {
    let patchBody: unknown;

    await page.route('**/v1/tenants/me/users/user-2', (route) => {
      if (route.request().method() === 'PATCH') {
        patchBody = JSON.parse(route.request().postData() ?? '{}');
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ...MOCK_USERS[1], role: 'admin' }),
        });
      }
    });

    await page.goto('/settings');

    // Find the role selector for editor@acme.com
    const memberRow = page.locator('[data-user-id="user-2"]');
    await memberRow.getByLabel(/role/i).selectOption('admin');
    await memberRow.getByRole('button', { name: /save/i }).click();

    expect(patchBody).toMatchObject({ role: 'admin' });
    await expect(memberRow.getByText(/admin/i)).toBeVisible();
  });

  test('non-admin cannot change roles (role selectors are disabled)', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem(
        'auth_user',
        JSON.stringify({ id: 'user-2', email: 'editor@acme.com', role: 'editor' }),
      );
    });

    await page.goto('/settings');

    const roleSelectors = page.locator('[data-user-id] [aria-label="role"]');
    const count = await roleSelectors.count();

    for (let i = 0; i < count; i++) {
      await expect(roleSelectors.nth(i)).toBeDisabled();
    }
  });

  // -------------------------------------------------------------------------
  // Verify access by role
  // -------------------------------------------------------------------------

  test('viewer cannot see invite button', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem(
        'auth_user',
        JSON.stringify({ id: 'user-3', email: 'viewer@acme.com', role: 'viewer' }),
      );
    });

    await page.goto('/settings');

    await expect(page.getByRole('button', { name: /invite/i })).not.toBeVisible();
  });

  test('editor can view team but cannot manage', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem(
        'auth_user',
        JSON.stringify({ id: 'user-2', email: 'editor@acme.com', role: 'editor' }),
      );
    });

    await page.goto('/settings');

    // Can view members
    await expect(page.getByText('admin@acme.com')).toBeVisible();

    // Cannot invite
    await expect(page.getByRole('button', { name: /invite/i })).not.toBeVisible();
  });
});
