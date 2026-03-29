<script lang="ts">
  /**
   * T146: Settings page — tenant config, team members, role management.
   */
  import { onMount } from 'svelte';
  import { apiClient, type TenantUser, type Role, ApiError } from '$lib/api';
  import { tenantStore } from '$lib/stores/tenant';
  import { isAdmin } from '$lib/stores/auth';
  import { PageHeader, Badge, Button, Card, Input, Select, Modal, LoadingSkeleton } from '$components/ui';

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
  const roleOptions = roles.map((r) => ({ value: r, label: r }));

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
  <PageHeader title="Settings" />

  <!-- Tenant info -->
  {#if $tenantStore.tenant}
    <Card>
      <h2 class="mb-4 text-lg font-semibold text-light-text">Workspace</h2>
      <dl class="grid grid-cols-2 gap-4 text-sm">
        <div>
          <dt class="text-light-text-secondary">Name</dt>
          <dd class="font-medium text-light-text">{$tenantStore.tenant.name}</dd>
        </div>
        <div>
          <dt class="text-light-text-secondary">Plan</dt>
          <dd>
            <Badge label={$tenantStore.tenant.plan} />
          </dd>
        </div>
        <div>
          <dt class="text-light-text-secondary">Contributors</dt>
          <dd class="font-medium text-light-text">{$tenantStore.tenant.contributor_count}</dd>
        </div>
        <div>
          <dt class="text-light-text-secondary">Repositories</dt>
          <dd class="font-medium text-light-text">{$tenantStore.tenant.repo_count}</dd>
        </div>
      </dl>
      <div class="mt-4">
        <a href="/settings/billing" class="text-sm text-primary-500 hover:underline">
          Manage plan & billing →
        </a>
      </div>
    </Card>
  {/if}

  <!-- Team members -->
  <Card>
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-lg font-semibold text-light-text">Team</h2>
      {#if $isAdmin}
        <Button size="sm" onclick={() => (showInviteModal = true)}>Invite</Button>
      {/if}
    </div>

    {#if inviteSuccess}
      <div class="mb-3 rounded-lg bg-success-light border border-success-border p-3 text-sm text-success-text">{inviteSuccess}</div>
    {/if}

    {#if roleError}
      <div class="mb-3 rounded-lg bg-error-light border border-error-border p-3 text-sm text-error-text">{roleError}</div>
    {/if}

    {#if loadingUsers}
      <div class="py-8">
        <LoadingSkeleton variant="text" lines={4} />
      </div>
    {:else if usersError}
      <div class="rounded-lg bg-error-light border border-error-border p-3 text-sm text-error-text">{usersError}</div>
    {:else}
      <ul class="space-y-3">
        {#each users as user}
          <li data-user-id={user.id} class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-light-text">{user.email}</p>
              <p class="text-xs text-light-text-muted">
                Joined {new Date(user.joined_at).toLocaleDateString()}
              </p>
            </div>

            <div class="flex items-center gap-2">
              <select
                aria-label="role"
                bind:value={pendingRoles[user.id]}
                disabled={!$isAdmin}
                class="rounded-lg border border-light-border-strong bg-light-bg text-light-text px-2 py-1 text-sm focus:border-primary-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
              >
                {#each roles as r}
                  <option value={r}>{r}</option>
                {/each}
              </select>

              {#if $isAdmin && pendingRoles[user.id] !== user.role}
                <Button
                  size="sm"
                  onclick={() => handleSaveRole(user)}
                  disabled={savingRole[user.id]}
                >Save</Button>
              {/if}
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  </Card>
</div>

<!-- Invite modal -->
<Modal
  bind:open={showInviteModal}
  onClose={() => { showInviteModal = false; inviteError = null; }}
  title="Invite team member"
>
  {#if inviteError}
    <div class="mb-3 rounded-lg bg-error-light border border-error-border p-3 text-sm text-error-text">{inviteError}</div>
  {/if}

  <div class="space-y-4">
    <Input
      label="Email"
      type="email"
      bind:value={inviteEmail}
      placeholder="colleague@company.com"
    />

    <Select
      label="Role"
      options={roleOptions}
      value={inviteRole}
      onchange={(v) => { inviteRole = v as Role; }}
    />
  </div>

  {#snippet footer()}
    <div class="flex justify-end gap-3">
      <Button
        variant="secondary"
        onclick={() => {
          showInviteModal = false;
          inviteError = null;
        }}
      >Cancel</Button>
      <Button
        onclick={handleInvite}
        disabled={inviting || !inviteEmail}
        loading={inviting}
      >
        {inviting ? 'Sending…' : 'Send invite'}
      </Button>
    </div>
  {/snippet}
</Modal>
