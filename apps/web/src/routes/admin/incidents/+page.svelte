<script lang="ts">
  /**
   * T051: Admin incidents page — total count, category/severity distribution, embedding coverage.
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
  <PageHeader title="Incidents Overview" description="Platform-wide incident statistics" />

  {#if error}
    <div class="bg-error-light border-error-border text-error-text rounded-lg border p-4 text-sm">
      <p>{error}</p>
      <Button variant="danger" size="sm" onclick={loadMetrics} class="mt-2">
        {#snippet children()}Retry{/snippet}
      </Button>
    </div>
  {:else if loading}
    <div class="grid grid-cols-1 gap-6 sm:grid-cols-3">
      {#each Array(3) as _}
        <LoadingSkeleton variant="card" />
      {/each}
    </div>
  {:else if metrics}
    <!-- Summary cards -->
    <div class="grid grid-cols-1 gap-6 sm:grid-cols-3">
      <MetricCard label="Total Incidents" value={metrics.incidents.total} />

      <MetricCard label="With Embeddings" value={metrics.incidents.with_embedding}>
        {#snippet children()}
          <p class="text-light-text-muted mt-1 text-sm">{embeddingPercent}% coverage</p>
        {/snippet}
      </MetricCard>

      <MetricCard label="Embedding Coverage" value="{embeddingPercent}%">
        {#snippet children()}
          <div class="mt-3">
            <div class="h-3 w-full rounded-full bg-neutral-200">
              <div
                class="bg-primary-500 h-3 rounded-full transition-all"
                style="width: {embeddingPercent}%"
              ></div>
            </div>
          </div>
        {/snippet}
      </MetricCard>
    </div>

    <!-- Category distribution -->
    <div class="mt-8">
      <h2 class="text-light-text mb-4 text-lg font-semibold">Category Distribution</h2>
      {#if categoryEntries.length > 0}
        <div class="border-light-border bg-light-bg rounded-xl border">
          <ul class="divide-light-border divide-y">
            {#each categoryEntries as [category, count]}
              <li class="flex items-center justify-between px-6 py-3">
                <span class="text-light-text-secondary text-sm font-medium">{category}</span>
                <div class="flex items-center gap-3">
                  <div class="h-2 w-24 rounded-full bg-neutral-200">
                    <div
                      class="bg-primary-500 h-2 rounded-full"
                      style="width: {metrics.incidents.total > 0
                        ? (count / metrics.incidents.total) * 100
                        : 0}%"
                    ></div>
                  </div>
                  <span class="text-light-text w-8 text-right text-sm font-medium">{count}</span>
                </div>
              </li>
            {/each}
          </ul>
        </div>
      {:else}
        <p class="text-light-text-muted text-sm">No category data available yet.</p>
      {/if}
    </div>

    <!-- Severity distribution -->
    <div class="mt-8">
      <h2 class="text-light-text mb-4 text-lg font-semibold">Findings by Severity (30d)</h2>
      {#if Object.keys(metrics.findings.by_severity).length > 0}
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {#each Object.entries(metrics.findings.by_severity) as [severity, count]}
            <div class="border-light-border bg-light-bg rounded-lg border p-4 text-center">
              <p class="text-light-text-secondary text-sm font-medium capitalize">{severity}</p>
              <p class="text-light-text mt-1 text-2xl font-bold">{count}</p>
            </div>
          {/each}
        </div>
      {:else}
        <p class="text-light-text-muted text-sm">No severity data available yet.</p>
      {/if}
    </div>
  {/if}
</div>
