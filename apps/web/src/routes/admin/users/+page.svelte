<script lang="ts">
  /**
   * T048: Admin users page — search, table, role/activation/tenant actions.
   */
  import { onMount } from 'svelte';
  import { apiClient, type AdminUser, type Role, ApiError } from '$lib/api';

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
  <div class="mb-6">
    <h1 class="text-2xl font-bold text-gray-900">Users</h1>
    <p class="mt-1 text-sm text-gray-500">
      Manage all platform users across tenants — {total} total
    </p>
  </div>

  <!-- Search -->
  <div class="mb-4">
    <input
      type="search"
      placeholder="Search by email or name..."
      bind:value={query}
      oninput={onQueryInput}
      class="w-full max-w-md rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
    />
  </div>

  <!-- Action error -->
  {#if actionError}
    <div class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{actionError}</div>
  {/if}

  <!-- Error -->
  {#if error}
    <div class="rounded-lg bg-red-50 p-4 text-sm text-red-700">
      <p>{error}</p>
      <button
        onclick={loadUsers}
        class="mt-2 rounded bg-red-100 px-3 py-1 text-sm font-medium text-red-700 hover:bg-red-200"
      >
        Retry
      </button>
    </div>
  {:else if loading}
    <div class="flex justify-center py-12">
      <span
        class="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent"
      ></span>
    </div>
  {:else if users.length === 0}
    <div
      class="rounded-xl border border-dashed border-gray-300 py-12 text-center text-sm text-gray-500"
    >
      No users found.
    </div>
  {:else}
    <div class="overflow-x-auto rounded-xl border border-gray-200 bg-white">
      <table class="w-full text-sm">
        <thead class="border-b border-gray-200 bg-gray-50">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Email</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Name</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Tenant</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Role</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Status</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Last Login</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Created</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          {#each users as user}
            <tr class="hover:bg-gray-50">
              <td class="px-4 py-3 font-medium text-gray-900">{user.email}</td>
              <td class="px-4 py-3 text-gray-600">{user.display_name ?? '—'}</td>
              <td class="px-4 py-3 text-gray-600">{user.tenant_name ?? '—'}</td>
              <td class="px-4 py-3">
                <span
                  class="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700 capitalize"
                >
                  {user.role}
                </span>
              </td>
              <td class="px-4 py-3">
                {#if user.is_active}
                  <span
                    class="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700"
                    >Active</span
                  >
                {:else}
                  <span class="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700"
                    >Inactive</span
                  >
                {/if}
              </td>
              <td class="px-4 py-3 text-xs text-gray-500">
                {user.last_login ? new Date(user.last_login).toLocaleDateString() : '—'}
              </td>
              <td class="px-4 py-3 text-xs text-gray-500">
                {new Date(user.created_at).toLocaleDateString()}
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-1">
                  <!-- Role dropdown -->
                  <div class="relative">
                    <button
                      onclick={() =>
                        (roleDropdownOpen = roleDropdownOpen === user.id ? null : user.id)}
                      class="rounded border border-gray-300 px-2 py-1 text-xs hover:bg-gray-100"
                      title="Change role"
                    >
                      Role
                    </button>
                    {#if roleDropdownOpen === user.id}
                      <div
                        class="absolute right-0 z-10 mt-1 w-28 rounded-md border border-gray-200 bg-white shadow-lg"
                      >
                        {#each roles as role}
                          <button
                            onclick={() => changeRole(user.id, role)}
                            class="block w-full px-3 py-1.5 text-left text-xs capitalize hover:bg-gray-100
                              {user.role === role ? 'font-bold text-indigo-600' : 'text-gray-700'}"
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
                    class="rounded border border-gray-300 px-2 py-1 text-xs hover:bg-gray-100"
                    title={user.is_active ? 'Deactivate' : 'Activate'}
                  >
                    {user.is_active ? 'Deactivate' : 'Activate'}
                  </button>

                  <!-- Assign tenant -->
                  <button
                    onclick={() => assignTenant(user.id)}
                    class="rounded border border-gray-300 px-2 py-1 text-xs hover:bg-gray-100"
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
      <div class="mt-4 flex items-center justify-between text-sm text-gray-500">
        <span>Page {page} of {totalPages}</span>
        <div class="flex gap-2">
          <button
            disabled={page <= 1}
            onclick={() => {
              page--;
              loadUsers();
            }}
            class="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
          >
            Previous
          </button>
          <button
            disabled={page >= totalPages}
            onclick={() => {
              page++;
              loadUsers();
            }}
            class="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    {/if}
  {/if}
</div>
