<script lang="ts">
  /**
   * T141: Incidents list page — text/semantic search + category/severity filters.
   */
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { apiClient, type Incident, type Category, type Severity, ApiError } from '$lib/api';
  import {
    PageHeader,
    Badge,
    Button,
    Input,
    Select,
    LoadingSkeleton,
    EmptyState,
  } from '$components/ui';
  import { Zap, Plus, Link } from 'lucide-svelte';

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
    'unsafe-regex',
    'race-condition',
    'missing-error-handling',
    'injection',
    'resource-exhaustion',
    'missing-safety-check',
    'deployment-error',
    'data-consistency',
    'unsafe-api-usage',
    'cascading-failure',
  ];

  const severities: Severity[] = ['critical', 'high', 'medium', 'low'];

  const categoryOptions = categories.map((c) => ({ value: c, label: c }));
  const severityOptions = severities.map((s) => ({ value: s, label: s }));

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
  <PageHeader title="Incidents" description="Post-mortem knowledge base — {total} total">
    {#snippet actions()}
      <a
        href="/incidents/ingest"
        class="border-light-border bg-light-bg text-light-text hover:bg-light-bg-hover inline-flex items-center gap-2 rounded-md border px-3.5 py-2 text-sm font-medium transition-colors"
      >
        <Link size={16} />
        Ingest from URL
      </a>
      <a
        href="/incidents/new"
        class="bg-primary-500 hover:bg-primary-600 inline-flex items-center gap-2 rounded-md px-3.5 py-2 text-sm font-medium text-white transition-colors"
      >
        <Plus size={16} />
        New incident
      </a>
    {/snippet}
  </PageHeader>

  <!-- Filters -->
  <div class="mb-4 flex flex-wrap gap-3">
    <div class="flex-1">
      <Input
        type="search"
        placeholder="Search incidents…"
        bind:value={query}
        oninput={onQueryInput}
      />
    </div>

    <label class="text-light-text-secondary flex items-center gap-2 text-sm">
      <input type="checkbox" bind:checked={semantic} onchange={onFilterChange} />
      Semantic search
    </label>

    <Select
      options={categoryOptions}
      value={filterCategory}
      placeholder="All categories"
      onchange={(v) => {
        filterCategory = v;
        onFilterChange();
      }}
    />

    <Select
      options={severityOptions}
      value={filterSeverity}
      placeholder="All severities"
      onchange={(v) => {
        filterSeverity = v;
        onFilterChange();
      }}
    />
  </div>

  <!-- Error -->
  {#if error}
    <div
      class="bg-error-light border-error-border text-error-text mb-4 rounded-lg border p-3 text-sm"
    >
      {error}
    </div>
  {/if}

  <!-- Table -->
  {#if loading}
    <div class="bg-light-bg border-light-border rounded-xl border p-6">
      <LoadingSkeleton variant="table-row" rows={5} />
    </div>
  {:else if incidents.length === 0}
    <div class="bg-light-bg border-light-border rounded-xl border">
      <EmptyState
        icon={Zap}
        title="No incidents found"
        description="Try adjusting your search or filters."
      />
    </div>
  {:else}
    <div class="border-light-border bg-light-bg overflow-hidden rounded-xl border">
      <table class="w-full text-sm">
        <thead class="border-light-border border-b">
          <tr>
            <th
              class="text-light-text-secondary px-4 py-3 text-left text-xs font-semibold tracking-wider uppercase"
              >Title</th
            >
            <th
              class="text-light-text-secondary px-4 py-3 text-left text-xs font-semibold tracking-wider uppercase"
              >Category</th
            >
            <th
              class="text-light-text-secondary px-4 py-3 text-left text-xs font-semibold tracking-wider uppercase"
              >Severity</th
            >
            <th
              class="text-light-text-secondary px-4 py-3 text-left text-xs font-semibold tracking-wider uppercase"
              >Languages</th
            >
            <th
              class="text-light-text-secondary px-4 py-3 text-left text-xs font-semibold tracking-wider uppercase"
              >Rule</th
            >
          </tr>
        </thead>
        <tbody class="divide-light-border divide-y">
          {#each incidents as incident}
            <tr
              class="hover:bg-light-bg-hover cursor-pointer transition-colors"
              onclick={() => goto(`/incidents/${incident.id}`)}
            >
              <td class="text-light-text px-4 py-3 font-medium">{incident.title}</td>
              <td class="text-light-text-secondary px-4 py-3">{incident.category}</td>
              <td class="px-4 py-3">
                <Badge severity={incident.severity} />
              </td>
              <td class="text-light-text-secondary px-4 py-3"
                >{incident.affected_languages.join(', ') || '—'}</td
              >
              <td class="px-4 py-3">
                {#if incident.linked_rule_id}
                  <a
                    href="/rules"
                    class="text-primary-500 hover:underline"
                    onclick={(e) => e.stopPropagation()}
                  >
                    {incident.linked_rule_id}
                  </a>
                {:else}
                  <span class="text-light-text-muted">—</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    {#if totalPages > 1}
      <div class="text-light-text-secondary mt-4 flex items-center justify-between text-sm">
        <span>Page {page} of {totalPages}</span>
        <div class="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={page <= 1}
            onclick={() => {
              page--;
              loadIncidents();
            }}>Previous</Button
          >
          <Button
            variant="secondary"
            size="sm"
            disabled={page >= totalPages}
            onclick={() => {
              page++;
              loadIncidents();
            }}>Next</Button
          >
        </div>
      </div>
    {/if}
  {/if}
</div>
