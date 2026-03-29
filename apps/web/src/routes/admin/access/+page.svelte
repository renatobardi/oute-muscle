<script lang="ts">
  /**
   * T053: Admin access control page — audit log table with filters.
   */
  import { onMount } from 'svelte';
  import { apiClient, type AdminAuditLogEntry, ApiError } from '$lib/api';

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
  <div class="mb-6">
    <h1 class="text-2xl font-bold text-gray-900">Access Control</h1>
    <p class="mt-1 text-sm text-gray-500">Platform-wide audit log — {total} entries</p>
  </div>

  <!-- Filters -->
  <div class="mb-4 flex flex-wrap gap-3">
    <select
      aria-label="entity type"
      bind:value={filterEntityType}
      onchange={onFilterChange}
      class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
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
      class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
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
      class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
    />

    <input
      type="date"
      aria-label="to date"
      bind:value={filterTo}
      onchange={onFilterChange}
      class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
    />
  </div>

  {#if error}
    <div class="rounded-lg bg-red-50 p-4 text-sm text-red-700">
      <p>{error}</p>
      <button
        onclick={loadAuditLog}
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
  {:else if entries.length === 0}
    <div
      class="rounded-xl border border-dashed border-gray-300 py-12 text-center text-sm text-gray-500"
    >
      No audit log entries found.
    </div>
  {:else}
    <div class="overflow-x-auto rounded-xl border border-gray-200 bg-white">
      <table class="w-full text-sm">
        <thead class="border-b border-gray-200 bg-gray-50">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Action</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Entity Type</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Entity ID</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Performed By</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Changes</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Date</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          {#each entries as entry}
            <tr class="hover:bg-gray-50">
              <td class="px-4 py-3">
                <span
                  class="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700"
                >
                  {entry.action}
                </span>
              </td>
              <td class="px-4 py-3 text-gray-600 capitalize">{entry.entity_type}</td>
              <td class="px-4 py-3 font-mono text-xs text-gray-500">
                {entry.entity_id.slice(0, 8)}...
              </td>
              <td class="px-4 py-3 text-xs text-gray-600">
                {entry.performed_by_email ?? entry.performed_by?.slice(0, 8) ?? '—'}
              </td>
              <td class="max-w-xs px-4 py-3">
                {#if entry.changes}
                  <pre
                    class="overflow-hidden text-xs text-ellipsis whitespace-nowrap text-gray-500">{JSON.stringify(
                      entry.changes
                    )}</pre>
                {:else}
                  <span class="text-gray-400">—</span>
                {/if}
              </td>
              <td class="px-4 py-3 text-xs text-gray-500">
                {new Date(entry.created_at).toLocaleString()}
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
              loadAuditLog();
            }}
            class="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
          >
            Previous
          </button>
          <button
            disabled={page >= totalPages}
            onclick={() => {
              page++;
              loadAuditLog();
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
