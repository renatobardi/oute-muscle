<script lang="ts">
  /**
   * T148: Audit log page — Enterprise only, chronological mutations.
   */
  import { onMount } from 'svelte';
  import { apiClient, type AuditLogEntry, ApiError } from '$lib/api';
  import { isEnterprise } from '$lib/stores/tenant';
  import { goto } from '$app/navigation';
  import { PageHeader, Badge, Button, Select, LoadingSkeleton, EmptyState } from '$components/ui';
  import { ScrollText } from 'lucide-svelte';

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

  const entityTypeOptions = [
    { value: 'incident', label: 'Incident' },
    { value: 'rule', label: 'Rule' },
    { value: 'scan', label: 'Scan' },
    { value: 'user', label: 'User' },
  ];

  const actionOptions = [
    { value: 'create', label: 'Create' },
    { value: 'update', label: 'Update' },
    { value: 'delete', label: 'Delete' },
  ];

  const actionBadgeMap: Record<string, 'active' | 'running' | 'failed'> = {
    create: 'active',
    update: 'running',
    delete: 'failed',
  };

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
  <PageHeader title="Audit Log" description="Immutable record of all mutations — {total} entries" />

  {#if !$isEnterprise}
    <div class="border-warning-border bg-warning-light rounded-xl border p-6 text-center">
      <p class="text-warning-text text-sm font-medium">
        Audit log is available on the Enterprise plan.
      </p>
      <a href="/settings/billing" class="text-warning-text mt-2 inline-block text-sm underline">
        Upgrade to Enterprise
      </a>
    </div>
  {:else}
    <!-- Filters -->
    <div class="mb-4 flex flex-wrap gap-3">
      <Select
        options={entityTypeOptions}
        value={filterEntityType}
        placeholder="All entity types"
        onchange={(v) => {
          filterEntityType = v;
          load();
        }}
      />

      <Select
        options={actionOptions}
        value={filterAction}
        placeholder="All actions"
        onchange={(v) => {
          filterAction = v;
          load();
        }}
      />

      <input
        type="date"
        aria-label="from date"
        bind:value={filterFrom}
        onchange={load}
        class="border-light-border-strong bg-light-bg text-light-text focus:border-primary-500 focus:ring-primary-500/20 h-11 rounded-lg border px-3 py-2.5 text-sm focus:ring-2 focus:outline-none"
      />

      <input
        type="date"
        aria-label="to date"
        bind:value={filterTo}
        onchange={load}
        class="border-light-border-strong bg-light-bg text-light-text focus:border-primary-500 focus:ring-primary-500/20 h-11 rounded-lg border px-3 py-2.5 text-sm focus:ring-2 focus:outline-none"
      />
    </div>

    {#if error}
      <div
        class="bg-error-light border-error-border text-error-text mb-4 rounded-lg border p-3 text-sm"
      >
        {error}
      </div>
    {/if}

    {#if loading}
      <div class="bg-light-bg border-light-border rounded-xl border p-6">
        <LoadingSkeleton variant="table-row" rows={5} />
      </div>
    {:else if entries.length === 0}
      <div class="bg-light-bg border-light-border rounded-xl border">
        <EmptyState
          icon={ScrollText}
          title="No audit log entries"
          description="Mutations will appear here as they happen."
        />
      </div>
    {:else}
      <div class="border-light-border bg-light-bg overflow-hidden rounded-xl border">
        <table class="w-full text-sm">
          <thead class="border-light-border border-b">
            <tr>
              <th
                class="text-light-text-secondary px-4 py-3 text-left text-xs font-semibold tracking-wider uppercase"
                >Time</th
              >
              <th
                class="text-light-text-secondary px-4 py-3 text-left text-xs font-semibold tracking-wider uppercase"
                >Actor</th
              >
              <th
                class="text-light-text-secondary px-4 py-3 text-left text-xs font-semibold tracking-wider uppercase"
                >Action</th
              >
              <th
                class="text-light-text-secondary px-4 py-3 text-left text-xs font-semibold tracking-wider uppercase"
                >Entity</th
              >
              <th
                class="text-light-text-secondary px-4 py-3 text-left text-xs font-semibold tracking-wider uppercase"
                >Entity ID</th
              >
            </tr>
          </thead>
          <tbody class="divide-light-border divide-y">
            {#each entries as entry}
              <tr class="hover:bg-light-bg-hover transition-colors">
                <td class="text-light-text-muted px-4 py-3 text-xs"
                  >{formatDate(entry.created_at)}</td
                >
                <td class="text-light-text px-4 py-3">{entry.actor_email}</td>
                <td class="px-4 py-3">
                  <Badge status={actionBadgeMap[entry.action] ?? undefined} label={entry.action} />
                </td>
                <td class="text-light-text px-4 py-3 capitalize">{entry.entity_type}</td>
                <td class="text-light-text-secondary px-4 py-3 font-mono text-xs"
                  >{entry.entity_id.slice(0, 12)}…</td
                >
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      {#if totalPages > 1}
        <div class="text-light-text-secondary mt-4 flex items-center justify-between text-sm">
          <span>Page {page} of {totalPages}</span>
          <div class="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={page <= 1}
              onclick={() => {
                page--;
                load();
              }}>Previous</Button
            >
            <Button
              variant="secondary"
              size="sm"
              disabled={page >= totalPages}
              onclick={() => {
                page++;
                load();
              }}>Next</Button
            >
          </div>
        </div>
      {/if}
    {/if}
  {/if}
</div>
