<script lang="ts">
  /**
   * T047: Admin overview page — summary cards with key platform metrics.
   */
  import { onMount } from 'svelte';
  import { apiClient, type AdminMetricsResponse, ApiError } from '$lib/api';
  import { PageHeader, MetricCard, LoadingSkeleton, Button } from '$components/ui';

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
  <PageHeader title="Admin Overview" description="Platform-wide metrics and health summary" />

  {#if error}
    <div class="bg-error-light border-error-border text-error-text rounded-lg border p-4 text-sm">
      <p>{error}</p>
      <Button variant="danger" size="sm" onclick={loadMetrics} class="mt-2">
        {#snippet children()}Retry{/snippet}
      </Button>
    </div>
  {:else if loading}
    <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {#each Array(6) as _}
        <LoadingSkeleton variant="card" />
      {/each}
    </div>
  {:else if metrics}
    <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <MetricCard label="Total Users" value={metrics.users.total}>
        {#snippet children()}
          <p class="text-light-text-muted mt-1 text-sm">
            {metrics!.users.active_30d} active in last 30d
          </p>
        {/snippet}
      </MetricCard>

      <MetricCard label="Tenants" value={metrics.tenants.total}>
        {#snippet children()}
          <p class="text-light-text-muted mt-1 text-sm">{metrics!.tenants.active} active</p>
        {/snippet}
      </MetricCard>

      <MetricCard label="Scans (30d)" value={metrics.scans.total_30d}>
        {#snippet children()}
          <p class="text-light-text-muted mt-1 text-sm">{metrics!.scans.active_now} running now</p>
        {/snippet}
      </MetricCard>

      <MetricCard label="Findings (30d)" value={metrics.findings.total_30d}>
        {#snippet children()}
          <p class="text-light-text-muted mt-1 text-sm">Across all tenants</p>
        {/snippet}
      </MetricCard>

      <MetricCard label="Incidents" value={metrics.incidents.total}>
        {#snippet children()}
          <p class="text-light-text-muted mt-1 text-sm">
            {metrics!.incidents.with_embedding} with embeddings ({metrics!.incidents.total > 0
              ? Math.round((metrics!.incidents.with_embedding / metrics!.incidents.total) * 100)
              : 0}%)
          </p>
        {/snippet}
      </MetricCard>

      <MetricCard label="Active Rules" value={metrics.rules.active}>
        {#snippet children()}
          <p class="text-light-text-muted mt-1 text-sm">
            {metrics!.rules.synthesis_pending} synthesis pending
          </p>
        {/snippet}
      </MetricCard>
    </div>

    <!-- LLM Usage -->
    <div class="mt-8">
      <h2 class="text-light-text mb-4 text-lg font-semibold">LLM Usage (30d)</h2>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div class="bg-light-bg border-light-border rounded-lg border p-4">
          <p class="text-light-text-secondary text-sm">Gemini Flash</p>
          <p class="text-light-text text-xl font-bold">{metrics.llm_usage_30d.flash}</p>
        </div>
        <div class="bg-light-bg border-light-border rounded-lg border p-4">
          <p class="text-light-text-secondary text-sm">Gemini Pro</p>
          <p class="text-light-text text-xl font-bold">{metrics.llm_usage_30d.pro}</p>
        </div>
        <div class="bg-light-bg border-light-border rounded-lg border p-4">
          <p class="text-light-text-secondary text-sm">Claude</p>
          <p class="text-light-text text-xl font-bold">{metrics.llm_usage_30d.claude}</p>
        </div>
      </div>
    </div>
  {/if}
</div>
