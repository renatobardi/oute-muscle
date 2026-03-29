<script lang="ts">
  /**
   * T050: Admin health page — request rate, latency, error rate, active scans, LLM usage.
   * Auto-refreshes every 60 seconds.
   */
  import { onMount, onDestroy } from 'svelte';
  import { apiClient, type AdminMetricsResponse, ApiError } from '$lib/api';

  let metrics = $state<AdminMetricsResponse | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let lastUpdated = $state<Date | null>(null);
  let intervalId: ReturnType<typeof setInterval>;

  async function loadMetrics() {
    error = null;
    try {
      metrics = await apiClient.admin.metrics();
      lastUpdated = new Date();
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Unable to load data';
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    loadMetrics();
    intervalId = setInterval(loadMetrics, 60_000);
  });

  onDestroy(() => {
    clearInterval(intervalId);
  });
</script>

<div>
  <div class="mb-8 flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Platform Health</h1>
      <p class="mt-1 text-sm text-gray-500">
        Real-time platform metrics
        {#if lastUpdated}
          — last updated {lastUpdated.toLocaleTimeString()}
        {/if}
      </p>
    </div>
    <button
      onclick={loadMetrics}
      class="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
    >
      Refresh
    </button>
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
    <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {#each Array(6) as _}
        <div class="animate-pulse rounded-xl border border-gray-200 bg-white p-6">
          <div class="h-4 w-24 rounded bg-gray-200"></div>
          <div class="mt-3 h-8 w-16 rounded bg-gray-200"></div>
        </div>
      {/each}
    </div>
  {:else if metrics}
    <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <!-- Scans -->
      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">Active Scans</p>
        <p class="mt-2 text-3xl font-bold text-gray-900">{metrics.scans.active_now}</p>
        <p class="mt-1 text-sm text-gray-400">{metrics.scans.total_30d} total in 30d</p>
      </div>

      <!-- Findings -->
      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">Findings (30d)</p>
        <p class="mt-2 text-3xl font-bold text-gray-900">{metrics.findings.total_30d}</p>
        <p class="mt-1 text-sm text-gray-400">Across all tenants</p>
      </div>

      <!-- Users active -->
      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">Active Users (30d)</p>
        <p class="mt-2 text-3xl font-bold text-gray-900">{metrics.users.active_30d}</p>
        <p class="mt-1 text-sm text-gray-400">of {metrics.users.total} total</p>
      </div>

      <!-- Active tenants -->
      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">Active Tenants</p>
        <p class="mt-2 text-3xl font-bold text-gray-900">{metrics.tenants.active}</p>
        <p class="mt-1 text-sm text-gray-400">of {metrics.tenants.total} total</p>
      </div>

      <!-- Rules -->
      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">Active Rules</p>
        <p class="mt-2 text-3xl font-bold text-gray-900">{metrics.rules.active}</p>
        <p class="mt-1 text-sm text-gray-400">{metrics.rules.synthesis_pending} synthesis pending</p>
      </div>

      <!-- Incidents with embedding -->
      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">Embedding Coverage</p>
        <p class="mt-2 text-3xl font-bold text-gray-900">
          {metrics.incidents.total > 0
            ? Math.round((metrics.incidents.with_embedding / metrics.incidents.total) * 100)
            : 0}%
        </p>
        <p class="mt-1 text-sm text-gray-400">
          {metrics.incidents.with_embedding} of {metrics.incidents.total} incidents
        </p>
      </div>
    </div>

    <!-- LLM Usage -->
    <div class="mt-8">
      <h2 class="mb-4 text-lg font-semibold text-gray-900">LLM Usage (30d)</h2>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div class="rounded-lg border border-gray-200 bg-white p-4">
          <p class="text-sm text-gray-500">Gemini Flash</p>
          <p class="text-xl font-bold text-gray-900">{metrics.llm_usage_30d.flash}</p>
        </div>
        <div class="rounded-lg border border-gray-200 bg-white p-4">
          <p class="text-sm text-gray-500">Gemini Pro</p>
          <p class="text-xl font-bold text-gray-900">{metrics.llm_usage_30d.pro}</p>
        </div>
        <div class="rounded-lg border border-gray-200 bg-white p-4">
          <p class="text-sm text-gray-500">Claude</p>
          <p class="text-xl font-bold text-gray-900">{metrics.llm_usage_30d.claude}</p>
        </div>
      </div>
    </div>

    <p class="mt-6 text-xs text-gray-400">Auto-refreshes every 60 seconds</p>
  {/if}
</div>
