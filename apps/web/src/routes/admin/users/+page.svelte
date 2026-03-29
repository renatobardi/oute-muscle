<script lang="ts">
  /**
   * T048: Admin users page — search, table, role/activation/tenant actions.
   */
  import { onMount } from 'svelte';
  import { apiClient, type AdminUser, type Role, ApiError } from '$lib/api';
  import { PageHeader, Badge, Button, EmptyState, LoadingSkeleton } from '$components/ui';

  let users = $state<AdminUser[]>([]);
  let total = $state(0);
  let page = $state(1);
  let perPage = 50;
  let loading = $state(true);
  let error = $state<string | null>(null);
  let actionError = $state<string | null>(null);

  let query = $state('');
  let debounceTimer: ReturnType<typeof setTimeout>;

  // Role change dropdown state
  let roleDropdownOpen = $state<string | null>(null);

  async function loadUsers() {
    loading = true;
    error = null;
    try {
      const result = await apiClient.admin.users.list({
        q: query || undefined,
        page,
        per_page: perPage,
      });
      users = result.items;
      total = result.total;
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Unable to load data';
    } finally {
      loading = false;
    }
  }

  function onQueryInput() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      page = 1;
      loadUsers();
    }, 300);
  }

  async function changeRole(userId: string, role: Role) {
    actionError = null;
    roleDropdownOpen = null;
    try {
      await apiClient.admin.users.changeRole(userId, role);
      await loadUsers();
    } catch (e) {
      actionError = e instanceof ApiError ? e.message : 'Failed to change role';
    }
  }

  async function toggleActive(user: AdminUser) {
    actionError = null;
    try {
      if (user.is_active) {
        await apiClient.admin.users.deactivate(user.id);
      } else {
        await apiClient.admin.users.activate(user.id);
      }
      await loadUsers();
    } catch (e) {
      actionError = e instanceof ApiError ? e.message : 'Failed to update user status';
    }
  }

  async function assignTenant(userId: string) {
    actionError = null;
    const tenantId = prompt('Enter tenant ID to assign:');
    if (!tenantId) return;
    try {
      await apiClient.admin.users.assignTenant(userId, tenantId);
      await loadUsers();
    } catch (e) {
      actionError = e instanceof ApiError ? e.message : 'Failed to assign tenant';
    }
  }

  onMount(loadUsers);

  const totalPages = $derived(Math.ceil(total / perPage));
  const roles: Role[] = ['admin', 'editor', 'viewer'];
</script>

<div>
  <PageHeader
    title="Users"
    description="Manage all platform users across tenants — {total} total"
  />

  <!-- Search -->
  <div class="mb-4">
    <input
      type="search"
      placeholder="Search by email or name..."
      bind:value={query}
      oninput={onQueryInput}
      class="w-full max-w-md rounded-lg border border-light-border px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 focus:outline-none"
    />
  </div>

  <!-- Action error -->
  {#if actionError}
    <div class="mb-4 rounded-lg bg-error-light border border-error-border p-3 text-sm text-error-text">{actionError}</div>
  {/if}

  <!-- Error -->
  {#if error}
    <div class="rounded-lg bg-error-light border border-error-border p-4 text-sm text-error-text">
      <p>{error}</p>
      <Button variant="danger" size="sm" onclick={loadUsers} class="mt-2">
        {#snippet children()}Retry{/snippet}
      </Button>
    </div>
  {:else if loading}
    <LoadingSkeleton variant="table-row" rows={8} />
  {:else if users.length === 0}
    <EmptyState title="No users found" description="Try adjusting your search query." />
  {:else}
    <div class="overflow-x-auto rounded-xl border border-light-border bg-light-bg">
      <table class="w-full text-sm">
        <thead class="border-b border-light-border-strong bg-light-bg-hover">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-light-text-secondary">Email</th>
            <th class="px-4 py-3 text-left font-medium text-light-text-secondary">Name</th>
            <th class="px-4 py-3 text-left font-medium text-light-text-secondary">Tenant</th>
            <th class="px-4 py-3 text-left font-medium text-light-text-secondary">Role</th>
            <th class="px-4 py-3 text-left font-medium text-light-text-secondary">Status</th>
            <th class="px-4 py-3 text-left font-medium text-light-text-secondary">Last Login</th>
            <th class="px-4 py-3 text-left font-medium text-light-text-secondary">Created</th>
            <th class="px-4 py-3 text-left font-medium text-light-text-secondary">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-light-border">
          {#each users as user}
            <tr class="hover:bg-light-bg-hover">
              <td class="px-4 py-3 font-medium text-light-text">{user.email}</td>
              <td class="px-4 py-3 text-light-text-secondary">{user.display_name ?? '—'}</td>
              <td class="px-4 py-3 text-light-text-secondary">{user.tenant_name ?? '—'}</td>
              <td class="px-4 py-3">
                <span
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize
                    {user.role === 'admin' ? 'bg-role-admin-light text-role-admin-text' :
                     user.role === 'editor' ? 'bg-role-editor-light text-role-editor-text' :
                     'bg-role-viewer-light text-role-viewer-text'}"
                >
                  {user.role}
                </span>
              </td>
              <td class="px-4 py-3">
                <Badge status={user.is_active ? 'active' : 'inactive'} label={user.is_active ? 'Active' : 'Inactive'} />
              </td>
              <td class="px-4 py-3 text-xs text-light-text-muted">
                {user.last_login ? new Date(user.last_login).toLocaleDateString() : '—'}
              </td>
              <td class="px-4 py-3 text-xs text-light-text-muted">
                {new Date(user.created_at).toLocaleDateString()}
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-1">
                  <!-- Role dropdown -->
                  <div class="relative">
                    <button
                      onclick={() =>
                        (roleDropdownOpen = roleDropdownOpen === user.id ? null : user.id)}
                      class="rounded border border-light-border px-2 py-1 text-xs hover:bg-light-bg-hover"
                      title="Change role"
                    >
                      Role
                    </button>
                    {#if roleDropdownOpen === user.id}
                      <div
                        class="absolute right-0 z-10 mt-1 w-28 rounded-md border border-light-border bg-light-bg shadow-lg"
                      >
                        {#each roles as role}
                          <button
                            onclick={() => changeRole(user.id, role)}
                            class="block w-full px-3 py-1.5 text-left text-xs capitalize hover:bg-light-bg-hover
                              {user.role === role ? 'font-bold text-primary-500' : 'text-light-text-secondary'}"
                          >
                            {role}
                          </button>
                        {/each}
                      </div>
                    {/if}
                  </div>

                  <!-- Activate / Deactivate -->
                  <button
                    onclick={() => toggleActive(user)}
                    class="rounded border border-light-border px-2 py-1 text-xs hover:bg-light-bg-hover"
                    title={user.is_active ? 'Deactivate' : 'Activate'}
                  >
                    {user.is_active ? 'Deactivate' : 'Activate'}
                  </button>

                  <!-- Assign tenant -->
                  <button
                    onclick={() => assignTenant(user.id)}
                    class="rounded border border-light-border px-2 py-1 text-xs hover:bg-light-bg-hover"
                    title="Assign tenant"
                  >
                    Tenant
                  </button>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    {#if totalPages > 1}
      <div class="mt-4 flex items-center justify-between text-sm text-light-text-muted">
        <span>Page {page} of {totalPages}</span>
        <div class="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={page <= 1}
            onclick={() => {
              page--;
              loadUsers();
            }}
          >
            {#snippet children()}Previous{/snippet}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={page >= totalPages}
            onclick={() => {
              page++;
              loadUsers();
            }}
          >
            {#snippet children()}Next{/snippet}
          </Button>
        </div>
      </div>
    {/if}
  {/if}
</div>
