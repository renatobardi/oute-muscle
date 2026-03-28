<script lang="ts">
  /**
   * T144: Rules list page — enable/disable toggles + incident links.
   */
  import { onMount } from 'svelte';
  import { apiClient, type Rule, type Category, ApiError } from '$lib/api';
  import { isAdmin } from '$lib/stores/auth';

  let rules = $state<Rule[]>([]);
  let total = $state(0);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let filterCategory = $state('');
  let filterEnabled = $state('');
  let toastError = $state<string | null>(null);

  const categories: Category[] = [
    'unsafe-regex', 'race-condition', 'missing-error-handling', 'injection',
    'resource-exhaustion', 'missing-safety-check', 'deployment-error',
    'data-consistency', 'unsafe-api-usage', 'cascading-failure',
  ];

  async function load() {
    loading = true;
    error = null;
    try {
      const result = await apiClient.rules.list({
        category: filterCategory || undefined,
        enabled: filterEnabled === '' ? undefined : filterEnabled === 'true',
      });
      rules = result.items;
      total = result.total;
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Failed to load rules';
    } finally {
      loading = false;
    }
  }

  async function handleToggle(rule: Rule) {
    toastError = null;
    const newEnabled = !rule.enabled;

    // Optimistic update
    rules = rules.map((r) => (r.id === rule.id ? { ...r, enabled: newEnabled } : r));

    try {
      await apiClient.rules.toggle(rule.id, newEnabled);
    } catch (e) {
      // Revert on failure
      rules = rules.map((r) => (r.id === rule.id ? { ...r, enabled: rule.enabled } : r));
      toastError = e instanceof ApiError ? e.message : 'Toggle failed';
    }
  }

  onMount(load);
</script>

<div>
  <div class="mb-6 flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Rules</h1>
      <p class="mt-1 text-sm text-gray-500">Semgrep rules — {total} total</p>
    </div>
  </div>

  <!-- Filters -->
  <div class="mb-4 flex gap-3">
    <select
      aria-label="category"
      bind:value={filterCategory}
      onchange={load}
      class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
    >
      <option value="">All categories</option>
      {#each categories as cat}
        <option value={cat}>{cat}</option>
      {/each}
    </select>

    <select
      bind:value={filterEnabled}
      onchange={load}
      class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
    >
      <option value="">All statuses</option>
      <option value="true">Enabled</option>
      <option value="false">Disabled</option>
    </select>
  </div>

  {#if toastError}
    <div class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{toastError}</div>
  {/if}

  {#if error}
    <div class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
  {/if}

  {#if loading}
    <div class="flex justify-center py-12">
      <span class="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent"></span>
    </div>
  {:else if rules.length === 0}
    <div class="rounded-xl border border-dashed border-gray-300 py-12 text-center text-sm text-gray-500">
      No rules found.
    </div>
  {:else}
    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
      <table class="w-full text-sm">
        <thead class="border-b border-gray-200 bg-gray-50">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Rule ID</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Category</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Severity</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Source</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Incident</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Status</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">YAML</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          {#each rules as rule}
            <tr data-rule-id={rule.id}>
              <td class="px-4 py-3 font-mono text-xs font-medium text-gray-900">{rule.id}</td>
              <td class="px-4 py-3 text-gray-500">{rule.category}</td>
              <td class="px-4 py-3 text-gray-500 capitalize">{rule.severity}</td>
              <td class="px-4 py-3">
                <span class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                  {rule.source}
                </span>
              </td>
              <td class="px-4 py-3">
                {#if rule.incident_title}
                  <a href="/incidents/{rule.incident_id}" class="text-indigo-600 hover:underline truncate max-w-xs block">
                    {rule.incident_title}
                  </a>
                {:else}
                  <span class="text-gray-400">—</span>
                {/if}
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <!-- Toggle switch -->
                  <button
                    role="switch"
                    aria-checked={rule.enabled}
                    disabled={!$isAdmin}
                    onclick={() => handleToggle(rule)}
                    class="relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent
                           transition-colors duration-200 ease-in-out focus:outline-none
                           {rule.enabled ? 'bg-indigo-600' : 'bg-gray-200'}
                           disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <span
                      class="inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                             {rule.enabled ? 'translate-x-4' : 'translate-x-0'}"
                    ></span>
                  </button>
                  <span class="text-xs {rule.enabled ? 'text-indigo-700' : 'text-gray-400'}">
                    {rule.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
              </td>
              <td class="px-4 py-3">
                <a
                  href="{import.meta.env.VITE_API_BASE_URL ?? 'https://api.outemuscle.com/v1'}/rules/{rule.id}/yaml"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-xs text-indigo-600 hover:underline"
                >
                  YAML ↗
                </a>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>
