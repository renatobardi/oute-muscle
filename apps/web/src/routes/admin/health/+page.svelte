<script lang="ts">
  /**
   * T050: Admin health page — request rate, latency, error rate, active scans, LLM usage.
   * Auto-refreshes every 60 seconds.
   */
  import { onMount, onDestroy } from 'svelte';
  import { apiClient, type AdminMetricsResponse, ApiError } from '$lib/api';
  import { PageHeader, MetricCard, LoadingSkeleton, Button } from '$components/ui';

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
  <PageHeader
    title="Platform Health"
    description="Real-time platform metrics{lastUpdated
      ? ` — last updated ${lastUpdated.toLocaleTimeString()}`
      : ''}"
  >
    {#snippet actions()}
      <Button variant="secondary" size="sm" onclick={loadMetrics}>
        {#snippet children()}Refresh{/snippet}
      </Button>
    {/snippet}
  </PageHeader>

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
      <MetricCard label="Active Scans" value={metrics.scans.active_now}>
        {#snippet children()}
          <p class="text-light-text-muted mt-1 text-sm">{metrics!.scans.total_30d} total in 30d</p>
        {/snippet}
      </MetricCard>

      <MetricCard label="Findings (30d)" value={metrics.findings.total_30d}>
        {#snippet children()}
          <p class="text-light-text-muted mt-1 text-sm">Across all tenants</p>
        {/snippet}
      </MetricCard>

      <MetricCard label="Active Users (30d)" value={metrics.users.active_30d}>
        {#snippet children()}
          <p class="text-light-text-muted mt-1 text-sm">of {metrics!.users.total} total</p>
        {/snippet}
      </MetricCard>

      <MetricCard label="Active Tenants" value={metrics.tenants.active}>
        {#snippet children()}
          <p class="text-light-text-muted mt-1 text-sm">of {metrics!.tenants.total} total</p>
        {/snippet}
      </MetricCard>

      <MetricCard label="Active Rules" value={metrics.rules.active}>
        {#snippet children()}
          <p class="text-light-text-muted mt-1 text-sm">
            {metrics!.rules.synthesis_pending} synthesis pending
          </p>
        {/snippet}
      </MetricCard>

      <MetricCard
        label="Embedding Coverage"
        value="{metrics.incidents.total > 0
          ? Math.round((metrics.incidents.with_embedding / metrics.incidents.total) * 100)
          : 0}%"
      >
        {#snippet children()}
          <p class="text-light-text-muted mt-1 text-sm">
            {metrics!.incidents.with_embedding} of {metrics!.incidents.total} incidents
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

    <p class="text-light-text-muted mt-6 text-xs">Auto-refreshes every 60 seconds</p>
  {/if}
</div>
