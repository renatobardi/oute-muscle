<script lang="ts">
  /**
   * T051: Admin incidents page — total count, category/severity distribution, embedding coverage.
   */
  import { onMount } from 'svelte';
  import { apiClient, type AdminMetricsResponse, ApiError } from '$lib/api';

  let metrics = $state<AdminMetricsResponse | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);

  async function loadMetrics() {
    loading = true;
    error = null;
    try {
      metrics = await apiClient.admin.metrics();
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Unable to load data';
    } finally {
      loading = false;
    }
  }

  onMount(loadMetrics);

  const embeddingPercent = $derived(
    metrics && metrics.incidents.total > 0
      ? Math.round((metrics.incidents.with_embedding / metrics.incidents.total) * 100)
      : 0
  );

  const categoryEntries = $derived(
    metrics ? Object.entries(metrics.incidents.by_category).sort((a, b) => b[1] - a[1]) : []
  );
</script>

<div>
  <div class="mb-8">
    <h1 class="text-2xl font-bold text-gray-900">Incidents Overview</h1>
    <p class="mt-1 text-sm text-gray-500">Platform-wide incident statistics</p>
  </div>

  {#if error}
    <div class="rounded-lg bg-red-50 p-4 text-sm text-red-700">
      <p>{error}</p>
      <button
        onclick={loadMetrics}
        class="mt-2 rounded bg-red-100 px-3 py-1 text-sm font-medium text-red-700 hover:bg-red-200"
      >
        Retry
      </button>
    </div>
  {:else if loading}
    <div class="grid grid-cols-1 gap-6 sm:grid-cols-3">
      {#each Array(3) as _}
        <div class="animate-pulse rounded-xl border border-gray-200 bg-white p-6">
          <div class="h-4 w-24 rounded bg-gray-200"></div>
          <div class="mt-3 h-8 w-16 rounded bg-gray-200"></div>
        </div>
      {/each}
    </div>
  {:else if metrics}
    <!-- Summary cards -->
    <div class="grid grid-cols-1 gap-6 sm:grid-cols-3">
      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">Total Incidents</p>
        <p class="mt-2 text-3xl font-bold text-gray-900">{metrics.incidents.total}</p>
      </div>

      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">With Embeddings</p>
        <p class="mt-2 text-3xl font-bold text-gray-900">{metrics.incidents.with_embedding}</p>
        <p class="mt-1 text-sm text-gray-400">{embeddingPercent}% coverage</p>
      </div>

      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">Embedding Coverage</p>
        <div class="mt-3">
          <div class="h-3 w-full rounded-full bg-gray-200">
            <div
              class="h-3 rounded-full bg-indigo-600 transition-all"
              style="width: {embeddingPercent}%"
            ></div>
          </div>
          <p class="mt-1 text-sm font-medium text-gray-700">{embeddingPercent}%</p>
        </div>
      </div>
    </div>

    <!-- Category distribution -->
    <div class="mt-8">
      <h2 class="mb-4 text-lg font-semibold text-gray-900">Category Distribution</h2>
      {#if categoryEntries.length > 0}
        <div class="rounded-xl border border-gray-200 bg-white">
          <ul class="divide-y divide-gray-100">
            {#each categoryEntries as [category, count]}
              <li class="flex items-center justify-between px-6 py-3">
                <span class="text-sm font-medium text-gray-700">{category}</span>
                <div class="flex items-center gap-3">
                  <div class="h-2 w-24 rounded-full bg-gray-200">
                    <div
                      class="h-2 rounded-full bg-indigo-500"
                      style="width: {metrics.incidents.total > 0
                        ? (count / metrics.incidents.total) * 100
                        : 0}%"
                    ></div>
                  </div>
                  <span class="w-8 text-right text-sm font-medium text-gray-900">{count}</span>
                </div>
              </li>
            {/each}
          </ul>
        </div>
      {:else}
        <p class="text-sm text-gray-500">No category data available yet.</p>
      {/if}
    </div>

    <!-- Severity distribution -->
    <div class="mt-8">
      <h2 class="mb-4 text-lg font-semibold text-gray-900">Findings by Severity (30d)</h2>
      {#if Object.keys(metrics.findings.by_severity).length > 0}
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {#each Object.entries(metrics.findings.by_severity) as [severity, count]}
            <div class="rounded-lg border border-gray-200 bg-white p-4 text-center">
              <p class="text-sm font-medium text-gray-500 capitalize">{severity}</p>
              <p class="mt-1 text-2xl font-bold text-gray-900">{count}</p>
            </div>
          {/each}
        </div>
      {:else}
        <p class="text-sm text-gray-500">No severity data available yet.</p>
      {/if}
    </div>
  {/if}
</div>
