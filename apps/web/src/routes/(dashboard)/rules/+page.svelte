<script lang="ts">
  /**
   * T144: Rules list page — enable/disable toggles + incident links.
   */
  import { onMount } from 'svelte';
  import { apiClient, type Rule, type Category, ApiError } from '$lib/api';
  import { isAdmin } from '$lib/stores/auth';
  import { PageHeader, Badge, Select, LoadingSkeleton, EmptyState } from '$components/ui';
  import { ShieldCheck } from 'lucide-svelte';

  let rules = $state<Rule[]>([]);
  let total = $state(0);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let filterCategory = $state('');
  let filterEnabled = $state('');
  let toastError = $state<string | null>(null);

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

  const categoryOptions = categories.map((c) => ({ value: c, label: c }));
  const statusOptions = [
    { value: 'true', label: 'Enabled' },
    { value: 'false', label: 'Disabled' },
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
  <PageHeader title="Rules" description="Semgrep rules — {total} total" />

  <!-- Filters -->
  <div class="mb-4 flex gap-3">
    <Select
      options={categoryOptions}
      value={filterCategory}
      placeholder="All categories"
      onchange={(v) => { filterCategory = v; load(); }}
    />

    <Select
      options={statusOptions}
      value={filterEnabled}
      placeholder="All statuses"
      onchange={(v) => { filterEnabled = v; load(); }}
    />
  </div>

  {#if toastError}
    <div class="mb-4 rounded-lg bg-error-light border border-error-border p-3 text-sm text-error-text">{toastError}</div>
  {/if}

  {#if error}
    <div class="mb-4 rounded-lg bg-error-light border border-error-border p-3 text-sm text-error-text">{error}</div>
  {/if}

  {#if loading}
    <div class="bg-light-bg rounded-xl border border-light-border p-6">
      <LoadingSkeleton variant="table-row" rows={5} />
    </div>
  {:else if rules.length === 0}
    <div class="bg-light-bg rounded-xl border border-light-border">
      <EmptyState
        icon={ShieldCheck}
        title="No rules found"
        description="Try adjusting your filters."
      />
    </div>
  {:else}
    <div class="overflow-hidden rounded-xl border border-light-border bg-light-bg">
      <table class="w-full text-sm">
        <thead class="border-b border-light-border">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Rule ID</th>
            <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Category</th>
            <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Severity</th>
            <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Source</th>
            <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Incident</th>
            <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">Status</th>
            <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-light-text-secondary">YAML</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-light-border">
          {#each rules as rule}
            <tr data-rule-id={rule.id} class="hover:bg-light-bg-hover transition-colors">
              <td class="px-4 py-3 font-mono text-xs font-medium text-light-text">{rule.id}</td>
              <td class="px-4 py-3 text-light-text-secondary">{rule.category}</td>
              <td class="px-4 py-3">
                <Badge severity={rule.severity} />
              </td>
              <td class="px-4 py-3">
                <Badge label={rule.source} />
              </td>
              <td class="px-4 py-3">
                {#if rule.incident_title}
                  <a
                    href="/incidents/{rule.incident_id}"
                    class="block max-w-xs truncate text-primary-500 hover:underline"
                  >
                    {rule.incident_title}
                  </a>
                {:else}
                  <span class="text-light-text-muted">—</span>
                {/if}
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <!-- Toggle switch -->
                  <button
                    role="switch"
                    aria-label="Toggle rule {rule.id}"
                    aria-checked={rule.enabled}
                    disabled={!$isAdmin}
                    onclick={() => handleToggle(rule)}
                    class="relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent
                           transition-colors duration-200 ease-in-out focus:outline-none
                           {rule.enabled ? 'bg-primary-500' : 'bg-neutral-300'}
                           disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <span
                      class="inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
                             {rule.enabled ? 'translate-x-4' : 'translate-x-0'}"
                    ></span>
                  </button>
                  <span class="text-xs {rule.enabled ? 'text-primary-500' : 'text-light-text-muted'}">
                    {rule.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
              </td>
              <td class="px-4 py-3">
                <a
                  href="{import.meta.env.VITE_API_BASE_URL ??
                    'https://muscle.oute.pro/api/v1'}/rules/{rule.id}/yaml"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-xs text-primary-500 hover:underline"
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
