<script lang="ts">
  /**
   * T147: Billing & usage page — plan limits, usage, upgrade prompts.
   */
  import { tenantStore, currentPlan, isTeamOrAbove, isEnterprise } from '$lib/stores/tenant';

  const PLANS = [
    {
      id: 'free',
      name: 'Free',
      price: '$0/mo',
      features: [
        '5 contributors',
        '3 repositories',
        'Layer 1 (Semgrep) only',
        '90-day findings retention',
      ],
    },
    {
      id: 'team',
      name: 'Team',
      price: '$49/mo',
      features: [
        '25 contributors',
        '25 repositories',
        'Layer 1 + Layer 2 (RAG advisory)',
        '1-year findings retention',
        'Priority support',
      ],
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      price: 'Custom',
      features: [
        'Unlimited contributors',
        'Unlimited repositories',
        'All 3 layers (L1 + L2 + L3 synthesis)',
        '2-year findings retention',
        'Audit log',
        'SSO / SAML',
        'Dedicated CSM',
      ],
    },
  ] as const;
</script>

<div class="mx-auto max-w-4xl">
  <a href="/settings" class="mb-6 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900">
    ← Back to settings
  </a>

  <h1 class="mb-8 text-2xl font-bold text-gray-900">Billing & Plan</h1>

  <!-- Current usage -->
  {#if $tenantStore.tenant}
    <div class="mb-8 rounded-xl border border-gray-200 bg-white p-6">
      <h2 class="mb-4 text-lg font-semibold text-gray-900">Current usage</h2>
      <div class="grid grid-cols-3 gap-6">
        <div>
          <p class="text-sm text-gray-500">Plan</p>
          <p class="mt-1 text-xl font-bold capitalize text-gray-900">{$tenantStore.tenant.plan}</p>
        </div>
        <div>
          <p class="text-sm text-gray-500">Contributors</p>
          <p class="mt-1 text-xl font-bold text-gray-900">{$tenantStore.tenant.contributor_count}</p>
        </div>
        <div>
          <p class="text-sm text-gray-500">Repositories</p>
          <p class="mt-1 text-xl font-bold text-gray-900">{$tenantStore.tenant.repo_count}</p>
        </div>
      </div>
    </div>
  {/if}

  <!-- Plan cards -->
  <div class="grid grid-cols-3 gap-6">
    {#each PLANS as plan}
      {@const isCurrent = $currentPlan === plan.id}
      <div
        class="relative rounded-xl border p-6 {isCurrent
          ? 'border-indigo-500 bg-indigo-50'
          : 'border-gray-200 bg-white'}"
      >
        {#if isCurrent}
          <span class="absolute right-4 top-4 rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">
            Current plan
          </span>
        {/if}

        <h3 class="text-lg font-bold text-gray-900">{plan.name}</h3>
        <p class="mt-1 text-2xl font-bold text-gray-900">{plan.price}</p>

        <ul class="mt-4 space-y-2">
          {#each plan.features as feature}
            <li class="flex items-start gap-2 text-sm text-gray-700">
              <span class="text-green-500">✓</span>
              {feature}
            </li>
          {/each}
        </ul>

        {#if !isCurrent}
          <button
            class="mt-6 w-full rounded-lg border border-indigo-600 px-4 py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-50"
          >
            {plan.id === 'enterprise' ? 'Contact sales' : 'Upgrade'}
          </button>
        {/if}
      </div>
    {/each}
  </div>
</div>
