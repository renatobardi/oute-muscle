<script lang="ts">
  /**
   * T049: Admin tenants page — table with plan/active filters.
   */
  import { onMount } from 'svelte';
  import { apiClient, type AdminTenant, ApiError } from '$lib/api';
  import { PageHeader, Badge, Button, EmptyState, LoadingSkeleton } from '$components/ui';

  let tenants = $state<AdminTenant[]>([]);
  let total = $state(0);
  let page = $state(1);
  let perPage = 50;
  let loading = $state(true);
  let error = $state<string | null>(null);

  let filterPlan = $state('');
  let filterActive = $state('');

  async function loadTenants() {
    loading = true;
    error = null;
    try {
      const result = await apiClient.admin.tenants.list({
        plan_tier: filterPlan || undefined,
        is_active: filterActive === '' ? undefined : filterActive === 'true',
        page,
        per_page: perPage,
      });
      tenants = result.items;
      total = result.total;
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Unable to load data';
    } finally {
      loading = false;
    }
  }

  function onFilterChange() {
    page = 1;
    loadTenants();
  }

  onMount(loadTenants);

  const totalPages = $derived(Math.ceil(total / perPage));
</script>

<div>
  <PageHeader
    title="Tenants"
    description="All registered tenants — {total} total"
  />

  <!-- Filters -->
  <div class="mb-4 flex gap-3">
    <select
      aria-label="plan tier"
      bind:value={filterPlan}
      onchange={onFilterChange}
      class="rounded-lg border border-light-border px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 focus:outline-none"
    >
      <option value="">All plans</option>
      <option value="free">Free</option>
      <option value="team">Team</option>
      <option value="enterprise">Enterprise</option>
    </select>

    <select
      aria-label="active status"
      bind:value={filterActive}
      onchange={onFilterChange}
      class="rounded-lg border border-light-border px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 focus:outline-none"
    >
      <option value="">All statuses</option>
      <option value="true">Active</option>
      <option value="false">Inactive</option>
    </select>
  </div>

  {#if error}
    <div class="rounded-lg bg-error-light border border-error-border p-4 text-sm text-error-text">
      <p>{error}</p>
      <Button variant="danger" size="sm" onclick={loadTenants} class="mt-2">
        {#snippet children()}Retry{/snippet}
      </Button>
    </div>
  {:else if loading}
    <LoadingSkeleton variant="table-row" rows={8} />
  {:else if tenants.length === 0}
    <EmptyState title="No tenants found" description="Try adjusting your filters." />
  {:else}
    <div class="overflow-x-auto rounded-xl border border-light-border bg-light-bg">
      <table class="w-full text-sm">
        <thead class="border-b border-light-border-strong bg-light-bg-hover">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-light-text-secondary">Name</th>
            <th class="px-4 py-3 text-left font-medium text-light-text-secondary">Plan</th>
            <th class="px-4 py-3 text-right font-medium text-light-text-secondary">Contributors</th>
            <th class="px-4 py-3 text-right font-medium text-light-text-secondary">Scans (30d)</th>
            <th class="px-4 py-3 text-right font-medium text-light-text-secondary">Findings (30d)</th>
            <th class="px-4 py-3 text-left font-medium text-light-text-secondary">Status</th>
            <th class="px-4 py-3 text-left font-medium text-light-text-secondary">Created</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-light-border">
          {#each tenants as tenant}
            <tr class="hover:bg-light-bg-hover">
              <td class="px-4 py-3 font-medium text-light-text">{tenant.name}</td>
              <td class="px-4 py-3">
                <span
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize
                    {tenant.plan_tier === 'free' ? 'bg-plan-free-light text-plan-free-text' :
                     tenant.plan_tier === 'team' ? 'bg-plan-team-light text-plan-team-text' :
                     'bg-plan-enterprise-light text-plan-enterprise-text'}"
                >
                  {tenant.plan_tier}
                </span>
              </td>
              <td class="px-4 py-3 text-right text-light-text-secondary">{tenant.contributor_count}</td>
              <td class="px-4 py-3 text-right text-light-text-secondary">{tenant.scan_count_30d}</td>
              <td class="px-4 py-3 text-right text-light-text-secondary">{tenant.findings_count_30d}</td>
              <td class="px-4 py-3">
                <Badge status={tenant.is_active ? 'active' : 'inactive'} label={tenant.is_active ? 'Active' : 'Inactive'} />
              </td>
              <td class="px-4 py-3 text-xs text-light-text-muted">
                {new Date(tenant.created_at).toLocaleDateString()}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    {#if totalPages > 1}
      <div class="mt-4 flex items-center justify-between text-sm text-light-text-muted">
        <span>Page {page} of {totalPages}</span>
        <div class="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={page <= 1}
            onclick={() => {
              page--;
              loadTenants();
            }}
          >
            {#snippet children()}Previous{/snippet}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={page >= totalPages}
            onclick={() => {
              page++;
              loadTenants();
            }}
          >
            {#snippet children()}Next{/snippet}
          </Button>
        </div>
      </div>
    {/if}
  {/if}
</div>
