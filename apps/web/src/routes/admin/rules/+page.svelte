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
  <div class="mb-8">
    <h1 class="text-2xl font-bold text-gray-900">Rules Overview</h1>
    <p class="mt-1 text-sm text-gray-500">Active rules and synthesis candidates</p>
  </div>

  {#if error}
    <div class="rounded-lg bg-red-50 p-4 text-sm text-red-700">
      <p>{error}</p>
      <button
        onclick={loadData}
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
        <p class="text-sm font-medium text-gray-500">Active Rules</p>
        <p class="mt-2 text-3xl font-bold text-gray-900">{metrics.rules.active}</p>
      </div>

      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">Auto-Disabled</p>
        <p class="mt-2 text-3xl font-bold text-gray-900">{metrics.rules.auto_disabled}</p>
      </div>

      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <p class="text-sm font-medium text-gray-500">Synthesis Pending</p>
        <p class="mt-2 text-3xl font-bold text-indigo-600">{metrics.rules.synthesis_pending}</p>
      </div>
    </div>

    <!-- Action error -->
    {#if actionError}
      <div class="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{actionError}</div>
    {/if}

    <!-- Pending candidates -->
    <div class="mt-8">
      <h2 class="mb-4 text-lg font-semibold text-gray-900">Pending Synthesis Candidates</h2>

      {#if candidates.length === 0}
        <div class="rounded-xl border border-dashed border-gray-300 py-8 text-center text-sm text-gray-500">
          No pending candidates.
        </div>
      {:else}
        <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table class="w-full text-sm">
            <thead class="border-b border-gray-200 bg-gray-50">
              <tr>
                <th class="px-4 py-3 text-left font-medium text-gray-500">Pattern Hash</th>
                <th class="px-4 py-3 text-right font-medium text-gray-500">Advisory Count</th>
                <th class="px-4 py-3 text-left font-medium text-gray-500">Created</th>
                <th class="px-4 py-3 text-left font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              {#each candidates as candidate}
                <tr class="hover:bg-gray-50">
                  <td class="px-4 py-3 font-mono text-xs text-gray-700">
                    {candidate.anti_pattern_hash.slice(0, 16)}...
                  </td>
                  <td class="px-4 py-3 text-right text-gray-600">{candidate.advisory_count}</td>
                  <td class="px-4 py-3 text-xs text-gray-500">
                    {new Date(candidate.created_at).toLocaleDateString()}
                  </td>
                  <td class="px-4 py-3">
                    <div class="flex gap-2">
                      <button
                        onclick={() => approve(candidate.id)}
                        class="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-500"
                      >
                        Approve
                      </button>
                      <button
                        onclick={() => reject(candidate.id)}
                        class="rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-500"
                      >
                        Reject
                      </button>
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
