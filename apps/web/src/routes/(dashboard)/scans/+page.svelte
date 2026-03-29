<script lang="ts">
  /**
   * T145: Scan results page — list of scans, risk trends, findings detail.
   */
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { apiClient, type Scan, type RiskLevel, ApiError } from '$lib/api';
  import {
    PageHeader,
    Badge,
    Button,
    Input,
    LoadingSkeleton,
    EmptyState,
    MetricCard,
  } from '$components/ui';
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
    <div class="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
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
  {:else if scans.length === 0}
    <div class="bg-light-bg border-light-border rounded-xl border">
      <EmptyState
        icon={ScanSearch}
        title="No scans yet"
        description="Connect your GitHub App or push code to trigger a scan."
      />
    </div>
  {:else}
    <div class="border-light-border bg-light-bg overflow-hidden rounded-xl border">
      <table class="w-full text-sm">
        <thead class="border-light-border border-b">
          <tr>
            <th
              class="text-light-text-secondary px-4 py-3 text-left text-xs font-semibold tracking-wider uppercase"
              >Repository</th
            >
            <th
              class="text-light-text-secondary px-4 py-3 text-left text-xs font-semibold tracking-wider uppercase"
              >Commit</th
            >
            <th
              class="text-light-text-secondary px-4 py-3 text-left text-xs font-semibold tracking-wider uppercase"
              >Risk</th
            >
            <th
              class="text-light-text-secondary px-4 py-3 text-left text-xs font-semibold tracking-wider uppercase"
              >Findings</th
            >
            <th
              class="text-light-text-secondary px-4 py-3 text-left text-xs font-semibold tracking-wider uppercase"
              >Duration</th
            >
            <th
              class="text-light-text-secondary px-4 py-3 text-left text-xs font-semibold tracking-wider uppercase"
              >Date</th
            >
          </tr>
        </thead>
        <tbody class="divide-light-border divide-y">
          {#each scans as scan}
            <tr
              class="hover:bg-light-bg-hover cursor-pointer transition-colors"
              onclick={() => goto(`/scans/${scan.id}`)}
            >
              <td class="text-light-text px-4 py-3 font-medium">{scan.repository}</td>
              <td class="text-light-text-secondary px-4 py-3 font-mono text-xs"
                >{scan.commit_sha.slice(0, 7)}</td
              >
              <td class="px-4 py-3">
                <Badge severity={scan.risk_level} />
              </td>
              <td class="text-light-text px-4 py-3">{scan.findings_count}</td>
              <td class="text-light-text-secondary px-4 py-3">{formatDuration(scan.duration_ms)}</td
              >
              <td class="text-light-text-muted px-4 py-3 text-xs">{formatDate(scan.created_at)}</td>
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
</div>
