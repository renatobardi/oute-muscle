<script lang="ts">
  /**
   * T145: Scan results page — list of scans, risk trends, findings detail.
   */
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { apiClient, type Scan, type RiskLevel, ApiError } from '$lib/api';

  let scans = $state<Scan[]>([]);
  let total = $state(0);
  let page = $state(1);
  let perPage = 20;
  let loading = $state(false);
  let error = $state<string | null>(null);
  let filterRepo = $state('');

  const riskColor: Record<RiskLevel, string> = {
    critical: 'bg-red-100 text-red-700',
    high: 'bg-orange-100 text-orange-700',
    medium: 'bg-yellow-100 text-yellow-700',
    low: 'bg-green-100 text-green-700',
  };

  // Risk level counts for summary bar
  const riskCounts = $derived(
    scans.reduce(
      (acc, s) => {
        acc[s.risk_level] = (acc[s.risk_level] ?? 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    ),
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
  <div class="mb-6 flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Scans</h1>
      <p class="mt-1 text-sm text-gray-500">{total} total scans</p>
    </div>
  </div>

  <!-- Risk summary bar -->
  {#if scans.length > 0}
    <div class="mb-6 flex gap-4">
      {#each (['critical', 'high', 'medium', 'low'] as RiskLevel[]) as level}
        {#if riskCounts[level]}
          <div class="rounded-lg border border-gray-200 bg-white px-4 py-3 text-center">
            <p class="text-2xl font-bold text-gray-900">{riskCounts[level]}</p>
            <p class="text-xs font-medium {riskColor[level].split(' ')[1]} capitalize">{level}</p>
          </div>
        {/if}
      {/each}
    </div>
  {/if}

  <!-- Filter -->
  <div class="mb-4 flex gap-3">
    <input
      type="text"
      placeholder="Filter by repository (e.g. org/repo)"
      bind:value={filterRepo}
      class="w-64 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
    />
    <button
      onclick={load}
      class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
    >Filter</button>
  </div>

  {#if error}
    <div class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
  {/if}

  {#if loading}
    <div class="flex justify-center py-12">
      <span class="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent"></span>
    </div>
  {:else if scans.length === 0}
    <div class="rounded-xl border border-dashed border-gray-300 py-12 text-center text-sm text-gray-500">
      No scans yet. Connect your GitHub App or push code to trigger a scan.
    </div>
  {:else}
    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
      <table class="w-full text-sm">
        <thead class="border-b border-gray-200 bg-gray-50">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Repository</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Commit</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Risk</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Findings</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Duration</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Date</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          {#each scans as scan}
            <tr class="cursor-pointer hover:bg-gray-50" onclick={() => goto(`/scans/${scan.id}`)}>
              <td class="px-4 py-3 font-medium text-gray-900">{scan.repository}</td>
              <td class="px-4 py-3 font-mono text-xs text-gray-500">{scan.commit_sha.slice(0, 7)}</td>
              <td class="px-4 py-3">
                <span class="rounded-full px-2 py-0.5 text-xs font-medium {riskColor[scan.risk_level]}">
                  {scan.risk_level}
                </span>
              </td>
              <td class="px-4 py-3 text-gray-700">{scan.findings_count}</td>
              <td class="px-4 py-3 text-gray-500">{formatDuration(scan.duration_ms)}</td>
              <td class="px-4 py-3 text-gray-400 text-xs">{formatDate(scan.created_at)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    {#if totalPages > 1}
      <div class="mt-4 flex items-center justify-between text-sm text-gray-500">
        <span>Page {page} of {totalPages}</span>
        <div class="flex gap-2">
          <button disabled={page <= 1} onclick={() => { page--; load(); }}
            class="rounded border border-gray-300 px-3 py-1 disabled:opacity-40">Previous</button>
          <button disabled={page >= totalPages} onclick={() => { page++; load(); }}
            class="rounded border border-gray-300 px-3 py-1 disabled:opacity-40">Next</button>
        </div>
      </div>
    {/if}
  {/if}
</div>
