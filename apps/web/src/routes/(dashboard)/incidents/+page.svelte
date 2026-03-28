<script lang="ts">
  /**
   * T141: Incidents list page — text/semantic search + category/severity filters.
   */
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { apiClient, type Incident, type Category, type Severity, ApiError } from '$lib/api';

  let incidents = $state<Incident[]>([]);
  let total = $state(0);
  let page = $state(1);
  let perPage = 20;
  let loading = $state(false);
  let error = $state<string | null>(null);

  let query = $state('');
  let semantic = $state(false);
  let filterCategory = $state('');
  let filterSeverity = $state('');

  let debounceTimer: ReturnType<typeof setTimeout>;

  const categories: Category[] = [
    'unsafe-regex', 'race-condition', 'missing-error-handling', 'injection',
    'resource-exhaustion', 'missing-safety-check', 'deployment-error',
    'data-consistency', 'unsafe-api-usage', 'cascading-failure',
  ];

  const severities: Severity[] = ['critical', 'high', 'medium', 'low'];

  const severityColor: Record<Severity, string> = {
    critical: 'bg-red-100 text-red-700',
    high: 'bg-orange-100 text-orange-700',
    medium: 'bg-yellow-100 text-yellow-700',
    low: 'bg-green-100 text-green-700',
  };

  async function loadIncidents() {
    loading = true;
    error = null;
    try {
      const result = await apiClient.incidents.list({
        q: query || undefined,
        semantic: semantic || undefined,
        category: filterCategory || undefined,
        severity: filterSeverity || undefined,
        page,
        per_page: perPage,
      });
      incidents = result.items;
      total = result.total;
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Failed to load incidents';
    } finally {
      loading = false;
    }
  }

  function onQueryInput() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      page = 1;
      loadIncidents();
    }, 300);
  }

  function onFilterChange() {
    page = 1;
    loadIncidents();
  }

  onMount(loadIncidents);

  const totalPages = $derived(Math.ceil(total / perPage));
</script>

<div>
  <!-- Header -->
  <div class="mb-6 flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Incidents</h1>
      <p class="mt-1 text-sm text-gray-500">Post-mortem knowledge base — {total} total</p>
    </div>
    <div class="flex gap-2">
      <a
        href="/incidents/ingest"
        class="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        Ingest from URL
      </a>
      <a
        href="/incidents/new"
        class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
      >
        New incident
      </a>
    </div>
  </div>

  <!-- Filters -->
  <div class="mb-4 flex flex-wrap gap-3">
    <input
      type="search"
      role="searchbox"
      placeholder="Search incidents…"
      bind:value={query}
      oninput={onQueryInput}
      class="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
    />

    <label class="flex items-center gap-2 text-sm text-gray-700">
      <input type="checkbox" bind:checked={semantic} onchange={onFilterChange} />
      Semantic search
    </label>

    <select
      aria-label="category"
      bind:value={filterCategory}
      onchange={onFilterChange}
      class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
    >
      <option value="">All categories</option>
      {#each categories as cat}
        <option value={cat}>{cat}</option>
      {/each}
    </select>

    <select
      bind:value={filterSeverity}
      onchange={onFilterChange}
      class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
    >
      <option value="">All severities</option>
      {#each severities as sev}
        <option value={sev}>{sev}</option>
      {/each}
    </select>
  </div>

  <!-- Error -->
  {#if error}
    <div class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
  {/if}

  <!-- Table -->
  {#if loading}
    <div class="flex justify-center py-12">
      <span class="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent"></span>
    </div>
  {:else if incidents.length === 0}
    <div class="rounded-xl border border-dashed border-gray-300 py-12 text-center text-sm text-gray-500">
      No incidents found.
    </div>
  {:else}
    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
      <table class="w-full text-sm">
        <thead class="border-b border-gray-200 bg-gray-50">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Title</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Category</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Severity</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Languages</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Rule</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          {#each incidents as incident}
            <tr
              class="cursor-pointer hover:bg-gray-50"
              onclick={() => goto(`/incidents/${incident.id}`)}
            >
              <td class="px-4 py-3 font-medium text-gray-900">{incident.title}</td>
              <td class="px-4 py-3 text-gray-500">{incident.category}</td>
              <td class="px-4 py-3">
                <span class="rounded-full px-2 py-0.5 text-xs font-medium {severityColor[incident.severity]}">
                  {incident.severity}
                </span>
              </td>
              <td class="px-4 py-3 text-gray-500">{incident.affected_languages.join(', ') || '—'}</td>
              <td class="px-4 py-3">
                {#if incident.linked_rule_id}
                  <a
                    href="/rules"
                    class="text-indigo-600 hover:underline"
                    onclick={(e) => e.stopPropagation()}
                  >
                    {incident.linked_rule_id}
                  </a>
                {:else}
                  <span class="text-gray-400">—</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    {#if totalPages > 1}
      <div class="mt-4 flex items-center justify-between text-sm text-gray-500">
        <span>Page {page} of {totalPages}</span>
        <div class="flex gap-2">
          <button
            disabled={page <= 1}
            onclick={() => { page--; loadIncidents(); }}
            class="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
          >Previous</button>
          <button
            disabled={page >= totalPages}
            onclick={() => { page++; loadIncidents(); }}
            class="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
          >Next</button>
        </div>
      </div>
    {/if}
  {/if}
</div>
