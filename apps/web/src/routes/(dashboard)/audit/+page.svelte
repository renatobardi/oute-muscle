<script lang="ts">
  /**
   * T148: Audit log page — Enterprise only, chronological mutations.
   */
  import { onMount } from 'svelte';
  import { apiClient, type AuditLogEntry, ApiError } from '$lib/api';
  import { isEnterprise } from '$lib/stores/tenant';
  import { goto } from '$app/navigation';
  import { PageHeader, Badge, Button, Select, Input, LoadingSkeleton, EmptyState } from '$components/ui';
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
    <div class="rounded-xl border border-warning-border bg-warning-light p-6 text-center">
      <p class="text-sm font-medium text-warning-text">
        Audit log is available on the Enterprise plan.
      </p>
      <a href="/settings/billing" class="mt-2 inline-block text-sm text-warning-text underline">
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
        onchange={(v) => { filterEntityType = v; load(); }}
      />

      <Select
        options={actionOptions}
        value={filterAction}
        placeholder="All actions"
        onchange={(v) => { filterAction = v; load(); }}
      />

      <input
        type="date"
        aria-label="from date"
        bind:value={filterFrom}
        onchange={load}
        class="rounded-lg border border-light-border-strong bg-light-bg text-light-text px-3 py-2.5 text-sm h-11 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none"
      />

      <input
        type="date"
        aria-label="to date"
        bind:value={filterTo}
        onchange={load}
        class="rounded-lg border border-light-border-strong bg-light-bg text-light-text px-3 py-2.5 text-sm h-11 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none"
      />
    </div>

    {#if error}
      <div class="mb-4 rounded-lg bg-error-light border border-error-border p-3 text-sm text-error-text">{error}</div>
    {/if}

    {#if loading}
      <div class="bg-light-bg rounded-xl border border-light-border p-6">
        <LoadingSkeleton variant="table-row" rows={5} />
      </div>
    {:else if entries.length === 0}
      <div class="bg-light-bg rounded-xl border border-light-border">
        <EmptyState
          icon={ScrollText}
          title="No audit log entries"
          description="Mutations will appear here as they happen."
        />
      </div>
    {:else}
      <div class="overflow-hidden rounded-xl border border-light-border bg-light-bg">
        <table class="w-full text-sm">
          <thead class="border-b border-light-border">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Time</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Actor</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Action</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Entity</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Entity ID</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-light-border">
            {#each entries as entry}
              <tr class="hover:bg-light-bg-hover transition-colors">
                <td class="px-4 py-3 text-xs text-light-text-muted">{formatDate(entry.created_at)}</td>
                <td class="px-4 py-3 text-light-text">{entry.actor_email}</td>
                <td class="px-4 py-3">
                  <Badge
                    status={actionBadgeMap[entry.action] ?? undefined}
                    label={entry.action}
                  />
                </td>
                <td class="px-4 py-3 text-light-text capitalize">{entry.entity_type}</td>
                <td class="px-4 py-3 font-mono text-xs text-light-text-secondary"
                  >{entry.entity_id.slice(0, 12)}…</td
                >
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      {#if totalPages > 1}
        <div class="mt-4 flex items-center justify-between text-sm text-light-text-secondary">
          <span>Page {page} of {totalPages}</span>
          <div class="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={page <= 1}
              onclick={() => {
                page--;
                load();
              }}
            >Previous</Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={page >= totalPages}
              onclick={() => {
                page++;
                load();
              }}
            >Next</Button>
          </div>
        </div>
      {/if}
    {/if}
  {/if}
</div>
