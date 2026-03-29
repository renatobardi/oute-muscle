<script lang="ts">
  /**
   * T053: Admin access control page — audit log table with filters.
   */
  import { onMount } from 'svelte';
  import { apiClient, type AdminAuditLogEntry, ApiError } from '$lib/api';
  import { PageHeader, Badge, Button, EmptyState, LoadingSkeleton } from '$components/ui';

  let entries = $state<AdminAuditLogEntry[]>([]);
  let total = $state(0);
  let page = $state(1);
  let perPage = 50;
  let loading = $state(true);
  let error = $state<string | null>(null);

  let filterEntityType = $state('');
  let filterAction = $state('');
  let filterFrom = $state('');
  let filterTo = $state('');

  async function loadAuditLog() {
    loading = true;
    error = null;
    try {
      const result = await apiClient.admin.auditLog.list({
        entity_type: filterEntityType || undefined,
        action: filterAction || undefined,
        from: filterFrom || undefined,
        to: filterTo || undefined,
        page,
        per_page: perPage,
      });
      entries = result.items;
      total = result.total;
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Unable to load data';
    } finally {
      loading = false;
    }
  }

  function onFilterChange() {
    page = 1;
    loadAuditLog();
  }

  onMount(loadAuditLog);

  const totalPages = $derived(Math.ceil(total / perPage));
</script>

<div>
  <PageHeader title="Access Control" description="Platform-wide audit log — {total} entries" />

  <!-- Filters -->
  <div class="mb-4 flex flex-wrap gap-3">
    <select
      aria-label="entity type"
      bind:value={filterEntityType}
      onchange={onFilterChange}
      class="border-light-border focus:border-primary-500 focus:ring-primary-500 rounded-lg border px-3 py-2 text-sm focus:ring-1 focus:outline-none"
    >
      <option value="">All entity types</option>
      <option value="user">User</option>
      <option value="tenant">Tenant</option>
      <option value="incident">Incident</option>
      <option value="rule">Rule</option>
      <option value="scan">Scan</option>
    </select>

    <select
      aria-label="action"
      bind:value={filterAction}
      onchange={onFilterChange}
      class="border-light-border focus:border-primary-500 focus:ring-primary-500 rounded-lg border px-3 py-2 text-sm focus:ring-1 focus:outline-none"
    >
      <option value="">All actions</option>
      <option value="create">Create</option>
      <option value="update">Update</option>
      <option value="delete">Delete</option>
      <option value="role_change">Role Change</option>
      <option value="deactivate">Deactivate</option>
      <option value="reactivate">Reactivate</option>
      <option value="assign_tenant">Assign Tenant</option>
    </select>

    <input
      type="date"
      aria-label="from date"
      bind:value={filterFrom}
      onchange={onFilterChange}
      class="border-light-border focus:border-primary-500 focus:ring-primary-500 rounded-lg border px-3 py-2 text-sm focus:ring-1 focus:outline-none"
    />

    <input
      type="date"
      aria-label="to date"
      bind:value={filterTo}
      onchange={onFilterChange}
      class="border-light-border focus:border-primary-500 focus:ring-primary-500 rounded-lg border px-3 py-2 text-sm focus:ring-1 focus:outline-none"
    />
  </div>

  {#if error}
    <div class="bg-error-light border-error-border text-error-text rounded-lg border p-4 text-sm">
      <p>{error}</p>
      <Button variant="danger" size="sm" onclick={loadAuditLog} class="mt-2">
        {#snippet children()}Retry{/snippet}
      </Button>
    </div>
  {:else if loading}
    <LoadingSkeleton variant="table-row" rows={8} />
  {:else if entries.length === 0}
    <EmptyState title="No audit log entries found" description="Try adjusting your filters." />
  {:else}
    <div class="border-light-border bg-light-bg overflow-x-auto rounded-xl border">
      <table class="w-full text-sm">
        <thead class="border-light-border-strong bg-light-bg-hover border-b">
          <tr>
            <th class="text-light-text-secondary px-4 py-3 text-left font-medium">Action</th>
            <th class="text-light-text-secondary px-4 py-3 text-left font-medium">Entity Type</th>
            <th class="text-light-text-secondary px-4 py-3 text-left font-medium">Entity ID</th>
            <th class="text-light-text-secondary px-4 py-3 text-left font-medium">Performed By</th>
            <th class="text-light-text-secondary px-4 py-3 text-left font-medium">Changes</th>
            <th class="text-light-text-secondary px-4 py-3 text-left font-medium">Date</th>
          </tr>
        </thead>
        <tbody class="divide-light-border divide-y">
          {#each entries as entry}
            <tr class="hover:bg-light-bg-hover">
              <td class="px-4 py-3">
                <Badge label={entry.action} dot={false} />
              </td>
              <td class="text-light-text-secondary px-4 py-3 capitalize">{entry.entity_type}</td>
              <td class="text-light-text-muted px-4 py-3 font-mono text-xs">
                {entry.entity_id.slice(0, 8)}...
              </td>
              <td class="text-light-text-secondary px-4 py-3 text-xs">
                {entry.performed_by_email ?? entry.performed_by?.slice(0, 8) ?? '—'}
              </td>
              <td class="max-w-xs px-4 py-3">
                {#if entry.changes}
                  <pre
                    class="text-light-text-muted overflow-hidden text-xs text-ellipsis whitespace-nowrap">{JSON.stringify(
                      entry.changes
                    )}</pre>
                {:else}
                  <span class="text-light-text-muted">—</span>
                {/if}
              </td>
              <td class="text-light-text-muted px-4 py-3 text-xs">
                {new Date(entry.created_at).toLocaleString()}
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
              loadAuditLog();
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
              loadAuditLog();
            }}
          >
            {#snippet children()}Next{/snippet}
          </Button>
        </div>
      </div>
    {/if}
  {/if}
</div>
