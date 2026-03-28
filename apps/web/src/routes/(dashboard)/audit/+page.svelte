<script lang="ts">
  /**
   * T148: Audit log page — Enterprise only, chronological mutations.
   */
  import { onMount } from 'svelte';
  import { apiClient, type AuditLogEntry, ApiError } from '$lib/api';
  import { isEnterprise } from '$lib/stores/tenant';
  import { goto } from '$app/navigation';

  let entries = $state<AuditLogEntry[]>([]);
  let total = $state(0);
  let page = $state(1);
  let perPage = 50;
  let loading = $state(false);
  let error = $state<string | null>(null);

  let filterEntityType = $state('');
  let filterAction = $state('');
  let filterFrom = $state('');
  let filterTo = $state('');

  async function load() {
    if (!$isEnterprise) return;
    loading = true;
    error = null;
    try {
      const result = await apiClient.auditLog.list({
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
      error = e instanceof ApiError ? e.message : 'Failed to load audit log';
    } finally {
      loading = false;
    }
  }

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleString();
  }

  const actionColor: Record<string, string> = {
    create: 'bg-green-100 text-green-700',
    update: 'bg-blue-100 text-blue-700',
    delete: 'bg-red-100 text-red-700',
  };

  onMount(async () => {
    if (!$isEnterprise) {
      await goto('/settings/billing');
      return;
    }
    await load();
  });

  const totalPages = $derived(Math.ceil(total / perPage));
</script>

<div>
  <div class="mb-6 flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Audit Log</h1>
      <p class="mt-1 text-sm text-gray-500">Immutable record of all mutations — {total} entries</p>
    </div>
  </div>

  {#if !$isEnterprise}
    <div class="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center">
      <p class="text-sm font-medium text-amber-800">
        Audit log is available on the Enterprise plan.
      </p>
      <a href="/settings/billing" class="mt-2 inline-block text-sm text-amber-700 underline">
        Upgrade to Enterprise
      </a>
    </div>
  {:else}
    <!-- Filters -->
    <div class="mb-4 flex flex-wrap gap-3">
      <select
        aria-label="entity type"
        bind:value={filterEntityType}
        onchange={load}
        class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
      >
        <option value="">All entity types</option>
        <option value="incident">Incident</option>
        <option value="rule">Rule</option>
        <option value="scan">Scan</option>
        <option value="user">User</option>
      </select>

      <select
        aria-label="action"
        bind:value={filterAction}
        onchange={load}
        class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
      >
        <option value="">All actions</option>
        <option value="create">Create</option>
        <option value="update">Update</option>
        <option value="delete">Delete</option>
      </select>

      <input
        type="date"
        aria-label="from date"
        bind:value={filterFrom}
        onchange={load}
        class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
      />

      <input
        type="date"
        aria-label="to date"
        bind:value={filterTo}
        onchange={load}
        class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
      />
    </div>

    {#if error}
      <div class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
    {/if}

    {#if loading}
      <div class="flex justify-center py-12">
        <span
          class="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent"
        ></span>
      </div>
    {:else if entries.length === 0}
      <div
        class="rounded-xl border border-dashed border-gray-300 py-12 text-center text-sm text-gray-500"
      >
        No audit log entries.
      </div>
    {:else}
      <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
        <table class="w-full text-sm">
          <thead class="border-b border-gray-200 bg-gray-50">
            <tr>
              <th class="px-4 py-3 text-left font-medium text-gray-500">Time</th>
              <th class="px-4 py-3 text-left font-medium text-gray-500">Actor</th>
              <th class="px-4 py-3 text-left font-medium text-gray-500">Action</th>
              <th class="px-4 py-3 text-left font-medium text-gray-500">Entity</th>
              <th class="px-4 py-3 text-left font-medium text-gray-500">Entity ID</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            {#each entries as entry}
              <tr class="hover:bg-gray-50">
                <td class="px-4 py-3 text-xs text-gray-400">{formatDate(entry.created_at)}</td>
                <td class="px-4 py-3 text-gray-700">{entry.actor_email}</td>
                <td class="px-4 py-3">
                  <span
                    class="rounded-full px-2 py-0.5 text-xs font-medium {actionColor[
                      entry.action
                    ] ?? 'bg-gray-100 text-gray-600'}"
                  >
                    {entry.action}
                  </span>
                </td>
                <td class="px-4 py-3 text-gray-700 capitalize">{entry.entity_type}</td>
                <td class="px-4 py-3 font-mono text-xs text-gray-500"
                  >{entry.entity_id.slice(0, 12)}…</td
                >
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      {#if totalPages > 1}
        <div class="mt-4 flex items-center justify-between text-sm text-gray-500">
          <span>Page {page} of {totalPages}</span>
          <div class="flex gap-2">
            <button
              disabled={page <= 1}
              onclick={() => {
                page--;
                load();
              }}
              class="rounded border border-gray-300 px-3 py-1 disabled:opacity-40">Previous</button
            >
            <button
              disabled={page >= totalPages}
              onclick={() => {
                page++;
                load();
              }}
              class="rounded border border-gray-300 px-3 py-1 disabled:opacity-40">Next</button
            >
          </div>
        </div>
      {/if}
    {/if}
  {/if}
</div>
