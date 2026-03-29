<script lang="ts">
  /**
   * T049: Admin tenants page — table with plan/active filters.
   */
  import { onMount } from 'svelte';
  import { apiClient, type AdminTenant, ApiError } from '$lib/api';

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
  <div class="mb-6">
    <h1 class="text-2xl font-bold text-gray-900">Tenants</h1>
    <p class="mt-1 text-sm text-gray-500">All registered tenants — {total} total</p>
  </div>

  <!-- Filters -->
  <div class="mb-4 flex gap-3">
    <select
      aria-label="plan tier"
      bind:value={filterPlan}
      onchange={onFilterChange}
      class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
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
      class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
    >
      <option value="">All statuses</option>
      <option value="true">Active</option>
      <option value="false">Inactive</option>
    </select>
  </div>

  {#if error}
    <div class="rounded-lg bg-red-50 p-4 text-sm text-red-700">
      <p>{error}</p>
      <button
        onclick={loadTenants}
        class="mt-2 rounded bg-red-100 px-3 py-1 text-sm font-medium text-red-700 hover:bg-red-200"
      >
        Retry
      </button>
    </div>
  {:else if loading}
    <div class="flex justify-center py-12">
      <span
        class="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent"
      ></span>
    </div>
  {:else if tenants.length === 0}
    <div
      class="rounded-xl border border-dashed border-gray-300 py-12 text-center text-sm text-gray-500"
    >
      No tenants found.
    </div>
  {:else}
    <div class="overflow-x-auto rounded-xl border border-gray-200 bg-white">
      <table class="w-full text-sm">
        <thead class="border-b border-gray-200 bg-gray-50">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Name</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Plan</th>
            <th class="px-4 py-3 text-right font-medium text-gray-500">Contributors</th>
            <th class="px-4 py-3 text-right font-medium text-gray-500">Scans (30d)</th>
            <th class="px-4 py-3 text-right font-medium text-gray-500">Findings (30d)</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Status</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Created</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          {#each tenants as tenant}
            <tr class="hover:bg-gray-50">
              <td class="px-4 py-3 font-medium text-gray-900">{tenant.name}</td>
              <td class="px-4 py-3">
                <span
                  class="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 capitalize"
                >
                  {tenant.plan_tier}
                </span>
              </td>
              <td class="px-4 py-3 text-right text-gray-600">{tenant.contributor_count}</td>
              <td class="px-4 py-3 text-right text-gray-600">{tenant.scan_count_30d}</td>
              <td class="px-4 py-3 text-right text-gray-600">{tenant.findings_count_30d}</td>
              <td class="px-4 py-3">
                {#if tenant.is_active}
                  <span
                    class="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700"
                    >Active</span
                  >
                {:else}
                  <span class="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700"
                    >Inactive</span
                  >
                {/if}
              </td>
              <td class="px-4 py-3 text-xs text-gray-500">
                {new Date(tenant.created_at).toLocaleDateString()}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    {#if totalPages > 1}
      <div class="mt-4 flex items-center justify-between text-sm text-gray-500">
        <span>Page {page} of {totalPages}</span>
        <div class="flex gap-2">
          <button
            disabled={page <= 1}
            onclick={() => {
              page--;
              loadTenants();
            }}
            class="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
          >
            Previous
          </button>
          <button
            disabled={page >= totalPages}
            onclick={() => {
              page++;
              loadTenants();
            }}
            class="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    {/if}
  {/if}
</div>
