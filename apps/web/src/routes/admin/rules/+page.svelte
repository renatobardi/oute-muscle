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
  <PageHeader title="Rules Overview" description="Active rules and synthesis candidates" />

  {#if error}
    <div class="bg-error-light border-error-border text-error-text rounded-lg border p-4 text-sm">
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
      <div
        class="bg-error-light border-error-border text-error-text mt-4 rounded-lg border p-3 text-sm"
      >
        {actionError}
      </div>
    {/if}

    <!-- Pending candidates -->
    <div class="mt-8">
      <h2 class="text-light-text mb-4 text-lg font-semibold">Pending Synthesis Candidates</h2>

      {#if candidates.length === 0}
        <EmptyState
          title="No pending candidates"
          description="All synthesis candidates have been reviewed."
        />
      {:else}
        <div class="border-light-border bg-light-bg overflow-hidden rounded-xl border">
          <table class="w-full text-sm">
            <thead class="border-light-border-strong bg-light-bg-hover border-b">
              <tr>
                <th class="text-light-text-secondary px-4 py-3 text-left font-medium"
                  >Pattern Hash</th
                >
                <th class="text-light-text-secondary px-4 py-3 text-right font-medium"
                  >Advisory Count</th
                >
                <th class="text-light-text-secondary px-4 py-3 text-left font-medium">Created</th>
                <th class="text-light-text-secondary px-4 py-3 text-left font-medium">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-light-border divide-y">
              {#each candidates as candidate}
                <tr class="hover:bg-light-bg-hover">
                  <td class="text-light-text-secondary px-4 py-3 font-mono text-xs">
                    {candidate.anti_pattern_hash.slice(0, 16)}...
                  </td>
                  <td class="text-light-text-secondary px-4 py-3 text-right"
                    >{candidate.advisory_count}</td
                  >
                  <td class="text-light-text-muted px-4 py-3 text-xs">
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
