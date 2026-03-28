<script lang="ts">
  /**
   * T146: Settings page — tenant config, team members, role management.
   */
  import { onMount } from 'svelte';
  import { apiClient, type TenantUser, type Role, ApiError } from '$lib/api';
  import { tenantStore, currentPlan } from '$lib/stores/tenant';
  import { isAdmin } from '$lib/stores/auth';

  let users = $state<TenantUser[]>([]);
  let loadingUsers = $state(false);
  let usersError = $state<string | null>(null);

  let showInviteModal = $state(false);
  let inviteEmail = $state('');
  let inviteRole = $state<Role>('editor');
  let inviting = $state(false);
  let inviteError = $state<string | null>(null);
  let inviteSuccess = $state<string | null>(null);

  let savingRole: Record<string, boolean> = {};
  let roleError = $state<string | null>(null);

  const roles: Role[] = ['admin', 'editor', 'viewer'];

  // Local role edits (before save)
  let pendingRoles = $state<Record<string, Role>>({});

  async function loadUsers() {
    loadingUsers = true;
    usersError = null;
    try {
      const result = await apiClient.tenants.users();
      users = result;
      pendingRoles = Object.fromEntries(result.map((u) => [u.id, u.role]));
    } catch (e) {
      usersError = e instanceof ApiError ? e.message : 'Failed to load team';
    } finally {
      loadingUsers = false;
    }
  }

  async function handleInvite() {
    inviting = true;
    inviteError = null;
    inviteSuccess = null;
    try {
      await apiClient.tenants.invite({ email: inviteEmail, role: inviteRole });
      inviteSuccess = 'Invitation sent';
      inviteEmail = '';
      showInviteModal = false;
      await loadUsers();
    } catch (e) {
      inviteError = e instanceof ApiError ? e.message : 'Invite failed';
    } finally {
      inviting = false;
    }
  }

  async function handleSaveRole(user: TenantUser) {
    roleError = null;
    savingRole[user.id] = true;
    try {
      await apiClient.tenants.updateUserRole(user.id, pendingRoles[user.id]);
      users = users.map((u) => (u.id === user.id ? { ...u, role: pendingRoles[user.id] } : u));
    } catch (e) {
      roleError = e instanceof ApiError ? e.message : 'Failed to update role';
      pendingRoles[user.id] = user.role; // revert
    } finally {
      savingRole[user.id] = false;
    }
  }

  onMount(loadUsers);
</script>

<div class="mx-auto max-w-3xl space-y-8">
  <h1 class="text-2xl font-bold text-gray-900">Settings</h1>

  <!-- Tenant info -->
  {#if $tenantStore.tenant}
    <section class="rounded-xl border border-gray-200 bg-white p-6">
      <h2 class="mb-4 text-lg font-semibold text-gray-900">Workspace</h2>
      <dl class="grid grid-cols-2 gap-4 text-sm">
        <div>
          <dt class="text-gray-500">Name</dt>
          <dd class="font-medium text-gray-900">{$tenantStore.tenant.name}</dd>
        </div>
        <div>
          <dt class="text-gray-500">Plan</dt>
          <dd>
            <span class="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium capitalize text-indigo-700">
              {$tenantStore.tenant.plan}
            </span>
          </dd>
        </div>
        <div>
          <dt class="text-gray-500">Contributors</dt>
          <dd class="font-medium text-gray-900">{$tenantStore.tenant.contributor_count}</dd>
        </div>
        <div>
          <dt class="text-gray-500">Repositories</dt>
          <dd class="font-medium text-gray-900">{$tenantStore.tenant.repo_count}</dd>
        </div>
      </dl>
      <div class="mt-4">
        <a href="/settings/billing" class="text-sm text-indigo-600 hover:underline">
          Manage plan & billing →
        </a>
      </div>
    </section>
  {/if}

  <!-- Team members -->
  <section class="rounded-xl border border-gray-200 bg-white p-6">
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-lg font-semibold text-gray-900">Team</h2>
      {#if $isAdmin}
        <button
          onclick={() => (showInviteModal = true)}
          class="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500"
        >
          Invite
        </button>
      {/if}
    </div>

    {#if inviteSuccess}
      <div class="mb-3 rounded-lg bg-green-50 p-3 text-sm text-green-700">{inviteSuccess}</div>
    {/if}

    {#if roleError}
      <div class="mb-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{roleError}</div>
    {/if}

    {#if loadingUsers}
      <div class="flex justify-center py-8">
        <span class="h-5 w-5 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent"></span>
      </div>
    {:else if usersError}
      <div class="rounded-lg bg-red-50 p-3 text-sm text-red-700">{usersError}</div>
    {:else}
      <ul class="space-y-3">
        {#each users as user}
          <li data-user-id={user.id} class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-900">{user.email}</p>
              <p class="text-xs text-gray-400">Joined {new Date(user.joined_at).toLocaleDateString()}</p>
            </div>

            <div class="flex items-center gap-2">
              <select
                aria-label="role"
                bind:value={pendingRoles[user.id]}
                disabled={!$isAdmin}
                class="rounded-lg border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none disabled:bg-gray-50 disabled:cursor-not-allowed"
              >
                {#each roles as r}
                  <option value={r}>{r}</option>
                {/each}
              </select>

              {#if $isAdmin && pendingRoles[user.id] !== user.role}
                <button
                  onclick={() => handleSaveRole(user)}
                  disabled={savingRole[user.id]}
                  class="rounded-lg bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-60"
                >Save</button>
              {/if}
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  </section>
</div>

<!-- Invite modal -->
{#if showInviteModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
    <div class="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
      <h2 class="mb-4 text-lg font-semibold text-gray-900">Invite team member</h2>

      {#if inviteError}
        <div class="mb-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{inviteError}</div>
      {/if}

      <div class="space-y-4">
        <div>
          <label for="invite-email" class="block text-sm font-medium text-gray-700">Email</label>
          <input
            id="invite-email"
            type="email"
            bind:value={inviteEmail}
            required
            class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            placeholder="colleague@company.com"
          />
        </div>

        <div>
          <label for="invite-role" class="block text-sm font-medium text-gray-700">Role</label>
          <select
            id="invite-role"
            bind:value={inviteRole}
            class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            {#each roles as r}
              <option value={r}>{r}</option>
            {/each}
          </select>
        </div>
      </div>

      <div class="mt-5 flex justify-end gap-3">
        <button
          onclick={() => { showInviteModal = false; inviteError = null; }}
          class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >Cancel</button>
        <button
          onclick={handleInvite}
          disabled={inviting || !inviteEmail}
          class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
        >
          {inviting ? 'Sending…' : 'Send invite'}
        </button>
      </div>
    </div>
  </div>
{/if}
