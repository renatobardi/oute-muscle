<script lang="ts">
  /**
   * T047: Admin overview page — summary cards with key platform metrics.
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
</script>

<div>
  <div class="mb-8">
    <h1 class="text-2xl font-bold text-gray-900">Admin Overview</h1>
    <p class="mt-1 text-sm text-gray-500">Platform-wide metrics and health summary</p>
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
          <div class="mt-2 h-3 w-32 rounded bg-gray-100"></div>
        </div>
      {/each}
    </div>
  {:else if metrics}
    <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <!-- Users -->
      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">Total Users</p>
        <p class="mt-2 text-3xl font-bold text-gray-900">{metrics.users.total}</p>
        <p class="mt-1 text-sm text-gray-400">{metrics.users.active_30d} active in last 30d</p>
      </div>

      <!-- Tenants -->
      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">Tenants</p>
        <p class="mt-2 text-3xl font-bold text-gray-900">{metrics.tenants.total}</p>
        <p class="mt-1 text-sm text-gray-400">{metrics.tenants.active} active</p>
      </div>

      <!-- Scans (30d) -->
      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">Scans (30d)</p>
        <p class="mt-2 text-3xl font-bold text-gray-900">{metrics.scans.total_30d}</p>
        <p class="mt-1 text-sm text-gray-400">{metrics.scans.active_now} running now</p>
      </div>

      <!-- Findings (30d) -->
      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">Findings (30d)</p>
        <p class="mt-2 text-3xl font-bold text-gray-900">{metrics.findings.total_30d}</p>
        <p class="mt-1 text-sm text-gray-400">Across all tenants</p>
      </div>

      <!-- Incidents -->
      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">Incidents</p>
        <p class="mt-2 text-3xl font-bold text-gray-900">{metrics.incidents.total}</p>
        <p class="mt-1 text-sm text-gray-400">
          {metrics.incidents.with_embedding} with embeddings
          ({metrics.incidents.total > 0
            ? Math.round((metrics.incidents.with_embedding / metrics.incidents.total) * 100)
            : 0}%)
        </p>
      </div>

      <!-- Rules -->
      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">Active Rules</p>
        <p class="mt-2 text-3xl font-bold text-gray-900">{metrics.rules.active}</p>
        <p class="mt-1 text-sm text-gray-400">{metrics.rules.synthesis_pending} synthesis pending</p>
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
  {/if}
</div>
