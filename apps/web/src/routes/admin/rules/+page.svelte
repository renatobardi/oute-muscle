<script lang="ts">
  /**
   * T052: Admin rules page — active rules, false positive rate, synthesis candidates.
   */
  import { onMount } from 'svelte';
  import {
    apiClient,
    type AdminMetricsResponse,
    type SynthesisCandidate,
    ApiError,
  } from '$lib/api';
  import { PageHeader, MetricCard, LoadingSkeleton, Button, EmptyState } from '$components/ui';

  let metrics = $state<AdminMetricsResponse | null>(null);
  let candidates = $state<SynthesisCandidate[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let actionError = $state<string | null>(null);

  async function loadData() {
    loading = true;
    error = null;
    try {
      const [metricsRes, candidatesRes] = await Promise.all([
        apiClient.admin.metrics(),
        apiClient.synthesis.listCandidates({ per_page: 20 }),
      ]);
      metrics = metricsRes;
      candidates = candidatesRes.items.filter((c) => c.status === 'pending');
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Unable to load data';
    } finally {
      loading = false;
    }
  }

  async function approve(id: string) {
    actionError = null;
    try {
      await apiClient.synthesis.approve(id);
      await loadData();
    } catch (e) {
      actionError = e instanceof ApiError ? e.message : 'Failed to approve candidate';
    }
  }

  async function reject(id: string) {
    actionError = null;
    try {
      await apiClient.synthesis.reject(id);
      await loadData();
    } catch (e) {
      actionError = e instanceof ApiError ? e.message : 'Failed to reject candidate';
    }
  }

  onMount(loadData);
</script>

<div>
  <PageHeader
    title="Rules Overview"
    description="Active rules and synthesis candidates"
  />

  {#if error}
    <div class="rounded-lg bg-error-light border border-error-border p-4 text-sm text-error-text">
      <p>{error}</p>
      <Button variant="danger" size="sm" onclick={loadData} class="mt-2">
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
      <MetricCard label="Active Rules" value={metrics.rules.active} />
      <MetricCard label="Auto-Disabled" value={metrics.rules.auto_disabled} />
      <MetricCard label="Synthesis Pending" value={metrics.rules.synthesis_pending} highlight />
    </div>

    <!-- Action error -->
    {#if actionError}
      <div class="mt-4 rounded-lg bg-error-light border border-error-border p-3 text-sm text-error-text">{actionError}</div>
    {/if}

    <!-- Pending candidates -->
    <div class="mt-8">
      <h2 class="mb-4 text-lg font-semibold text-light-text">Pending Synthesis Candidates</h2>

      {#if candidates.length === 0}
        <EmptyState title="No pending candidates" description="All synthesis candidates have been reviewed." />
      {:else}
        <div class="overflow-hidden rounded-xl border border-light-border bg-light-bg">
          <table class="w-full text-sm">
            <thead class="border-b border-light-border-strong bg-light-bg-hover">
              <tr>
                <th class="px-4 py-3 text-left font-medium text-light-text-secondary">Pattern Hash</th>
                <th class="px-4 py-3 text-right font-medium text-light-text-secondary">Advisory Count</th>
                <th class="px-4 py-3 text-left font-medium text-light-text-secondary">Created</th>
                <th class="px-4 py-3 text-left font-medium text-light-text-secondary">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-light-border">
              {#each candidates as candidate}
                <tr class="hover:bg-light-bg-hover">
                  <td class="px-4 py-3 font-mono text-xs text-light-text-secondary">
                    {candidate.anti_pattern_hash.slice(0, 16)}...
                  </td>
                  <td class="px-4 py-3 text-right text-light-text-secondary">{candidate.advisory_count}</td>
                  <td class="px-4 py-3 text-xs text-light-text-muted">
                    {new Date(candidate.created_at).toLocaleDateString()}
                  </td>
                  <td class="px-4 py-3">
                    <div class="flex gap-2">
                      <Button variant="primary" size="sm" onclick={() => approve(candidate.id)}>
                        {#snippet children()}Approve{/snippet}
                      </Button>
                      <Button variant="danger" size="sm" onclick={() => reject(candidate.id)}>
                        {#snippet children()}Reject{/snippet}
                      </Button>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {/if}
</div>
