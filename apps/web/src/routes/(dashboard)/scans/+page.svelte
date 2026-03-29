<script lang="ts">
  /**
   * T145: Scan results page — list of scans, risk trends, findings detail.
   */
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { apiClient, type Scan, type RiskLevel, ApiError } from '$lib/api';
  import { PageHeader, Badge, Button, Input, LoadingSkeleton, EmptyState, MetricCard } from '$components/ui';
  import { ScanSearch } from 'lucide-svelte';

  let scans = $state<Scan[]>([]);
  let total = $state(0);
  let page = $state(1);
  let perPage = 20;
  let loading = $state(false);
  let error = $state<string | null>(null);
  let filterRepo = $state('');

  // Risk level counts for summary bar
  const riskCounts = $derived(
    scans.reduce(
      (acc, s) => {
        acc[s.risk_level] = (acc[s.risk_level] ?? 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    )
  );

  async function load() {
    loading = true;
    error = null;
    try {
      const result = await apiClient.scans.list({
        repository: filterRepo || undefined,
        page,
        per_page: perPage,
      });
      scans = result.items;
      total = result.total;
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Failed to load scans';
    } finally {
      loading = false;
    }
  }

  function formatDuration(ms: number): string {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  }

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleString();
  }

  onMount(load);

  const totalPages = $derived(Math.ceil(total / perPage));
</script>

<div>
  <PageHeader title="Scans" description="{total} total scans" />

  <!-- Risk summary bar -->
  {#if scans.length > 0}
    <div class="mb-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
      {#each ['critical', 'high', 'medium', 'low'] as RiskLevel[] as level}
        {#if riskCounts[level]}
          <MetricCard label={level} value={riskCounts[level]} />
        {/if}
      {/each}
    </div>
  {/if}

  <!-- Filter -->
  <div class="mb-4 flex gap-3">
    <div class="w-64">
      <Input
        type="text"
        placeholder="Filter by repository (e.g. org/repo)"
        bind:value={filterRepo}
      />
    </div>
    <Button variant="secondary" onclick={load}>Filter</Button>
  </div>

  {#if error}
    <div class="mb-4 rounded-lg bg-error-light border border-error-border p-3 text-sm text-error-text">{error}</div>
  {/if}

  {#if loading}
    <div class="bg-light-bg rounded-xl border border-light-border p-6">
      <LoadingSkeleton variant="table-row" rows={5} />
    </div>
  {:else if scans.length === 0}
    <div class="bg-light-bg rounded-xl border border-light-border">
      <EmptyState
        icon={ScanSearch}
        title="No scans yet"
        description="Connect your GitHub App or push code to trigger a scan."
      />
    </div>
  {:else}
    <div class="overflow-hidden rounded-xl border border-light-border bg-light-bg">
      <table class="w-full text-sm">
        <thead class="border-b border-light-border">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Repository</th>
            <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Commit</th>
            <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Risk</th>
            <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Findings</th>
            <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Duration</th>
            <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Date</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-light-border">
          {#each scans as scan}
            <tr class="cursor-pointer hover:bg-light-bg-hover transition-colors" onclick={() => goto(`/scans/${scan.id}`)}>
              <td class="px-4 py-3 font-medium text-light-text">{scan.repository}</td>
              <td class="px-4 py-3 font-mono text-xs text-light-text-secondary"
                >{scan.commit_sha.slice(0, 7)}</td
              >
              <td class="px-4 py-3">
                <Badge severity={scan.risk_level} />
              </td>
              <td class="px-4 py-3 text-light-text">{scan.findings_count}</td>
              <td class="px-4 py-3 text-light-text-secondary">{formatDuration(scan.duration_ms)}</td>
              <td class="px-4 py-3 text-xs text-light-text-muted">{formatDate(scan.created_at)}</td>
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
</div>
