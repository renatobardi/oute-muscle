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
      class="border-light-border focus:border-primary-500 focus:ring-primary-500 w-full max-w-md rounded-lg border px-3 py-2 text-sm focus:ring-1 focus:outline-none"
    />
  </div>

  <!-- Action error -->
  {#if actionError}
    <div
      class="bg-error-light border-error-border text-error-text mb-4 rounded-lg border p-3 text-sm"
    >
      {actionError}
    </div>
  {/if}

  <!-- Error -->
  {#if error}
    <div class="bg-error-light border-error-border text-error-text rounded-lg border p-4 text-sm">
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
    <div class="border-light-border bg-light-bg overflow-x-auto rounded-xl border">
      <table class="w-full text-sm">
        <thead class="border-light-border-strong bg-light-bg-hover border-b">
          <tr>
            <th class="text-light-text-secondary px-4 py-3 text-left font-medium">Email</th>
            <th class="text-light-text-secondary px-4 py-3 text-left font-medium">Name</th>
            <th class="text-light-text-secondary px-4 py-3 text-left font-medium">Tenant</th>
            <th class="text-light-text-secondary px-4 py-3 text-left font-medium">Role</th>
            <th class="text-light-text-secondary px-4 py-3 text-left font-medium">Status</th>
            <th class="text-light-text-secondary px-4 py-3 text-left font-medium">Last Login</th>
            <th class="text-light-text-secondary px-4 py-3 text-left font-medium">Created</th>
            <th class="text-light-text-secondary px-4 py-3 text-left font-medium">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-light-border divide-y">
          {#each users as user}
            <tr class="hover:bg-light-bg-hover">
              <td class="text-light-text px-4 py-3 font-medium">{user.email}</td>
              <td class="text-light-text-secondary px-4 py-3">{user.display_name ?? '—'}</td>
              <td class="text-light-text-secondary px-4 py-3">{user.tenant_name ?? '—'}</td>
              <td class="px-4 py-3">
                <span
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize
                    {user.role === 'admin'
                    ? 'bg-role-admin-light text-role-admin-text'
                    : user.role === 'editor'
                      ? 'bg-role-editor-light text-role-editor-text'
                      : 'bg-role-viewer-light text-role-viewer-text'}"
                >
                  {user.role}
                </span>
              </td>
              <td class="px-4 py-3">
                <Badge
                  status={user.is_active ? 'active' : 'inactive'}
                  label={user.is_active ? 'Active' : 'Inactive'}
                />
              </td>
              <td class="text-light-text-muted px-4 py-3 text-xs">
                {user.last_login ? new Date(user.last_login).toLocaleDateString() : '—'}
              </td>
              <td class="text-light-text-muted px-4 py-3 text-xs">
                {new Date(user.created_at).toLocaleDateString()}
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-1">
                  <!-- Role dropdown -->
                  <div class="relative">
                    <button
                      onclick={() =>
                        (roleDropdownOpen = roleDropdownOpen === user.id ? null : user.id)}
                      class="border-light-border hover:bg-light-bg-hover rounded border px-2 py-1 text-xs"
                      title="Change role"
                    >
                      Role
                    </button>
                    {#if roleDropdownOpen === user.id}
                      <div
                        class="border-light-border bg-light-bg absolute right-0 z-10 mt-1 w-28 rounded-md border shadow-lg"
                      >
                        {#each roles as role}
                          <button
                            onclick={() => changeRole(user.id, role)}
                            class="hover:bg-light-bg-hover block w-full px-3 py-1.5 text-left text-xs capitalize
                              {user.role === role
                              ? 'text-primary-500 font-bold'
                              : 'text-light-text-secondary'}"
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
                    class="border-light-border hover:bg-light-bg-hover rounded border px-2 py-1 text-xs"
                    title={user.is_active ? 'Deactivate' : 'Activate'}
                  >
                    {user.is_active ? 'Deactivate' : 'Activate'}
                  </button>

                  <!-- Assign tenant -->
                  <button
                    onclick={() => assignTenant(user.id)}
                    class="border-light-border hover:bg-light-bg-hover rounded border px-2 py-1 text-xs"
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
      <div class="text-light-text-muted mt-4 flex items-center justify-between text-sm">
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
