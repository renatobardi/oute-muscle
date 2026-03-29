<script lang="ts">
  /**
   * T147: Billing & usage page — plan limits, usage, upgrade prompts.
   */
  import { tenantStore, currentPlan } from '$lib/stores/tenant';
  import { Button, Card, Badge, PageHeader } from '$components/ui';

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
  <a
    href="/settings"
    class="text-light-text-muted hover:text-light-text mb-6 inline-flex items-center gap-1 text-sm"
  >
    ← Back to settings
  </a>

  <PageHeader title="Billing & Plan" />

  <!-- Current usage -->
  {#if $tenantStore.tenant}
    <Card class="mb-8">
      <h2 class="text-light-text mb-4 text-lg font-semibold">Current usage</h2>
      <div class="grid grid-cols-3 gap-6">
        <div>
          <p class="text-light-text-secondary text-sm">Plan</p>
          <p class="text-light-text mt-1 text-xl font-bold capitalize">
            {$tenantStore.tenant.plan}
          </p>
        </div>
        <div>
          <p class="text-light-text-secondary text-sm">Contributors</p>
          <p class="text-light-text mt-1 text-xl font-bold">
            {$tenantStore.tenant.contributor_count}
          </p>
        </div>
        <div>
          <p class="text-light-text-secondary text-sm">Repositories</p>
          <p class="text-light-text mt-1 text-xl font-bold">{$tenantStore.tenant.repo_count}</p>
        </div>
      </div>
    </Card>
  {/if}

  <!-- Plan cards -->
  <div class="grid grid-cols-3 gap-6">
    {#each PLANS as plan}
      {@const isCurrent = $currentPlan === plan.id}
      <Card class={isCurrent ? 'border-primary-500 bg-primary-50/30' : ''}>
        <div class="relative">
          {#if isCurrent}
            <div class="absolute top-0 right-0">
              <Badge status="active" label="Current plan" />
            </div>
          {/if}

          <h3 class="text-light-text text-lg font-bold">{plan.name}</h3>
          <p class="text-light-text mt-1 text-2xl font-bold">{plan.price}</p>

          <ul class="mt-4 space-y-2">
            {#each plan.features as feature}
              <li class="text-light-text-secondary flex items-start gap-2 text-sm">
                <span class="text-status-active">&#10003;</span>
                {feature}
              </li>
            {/each}
          </ul>

          {#if !isCurrent}
            <div class="mt-6">
              <Button variant="secondary" class="w-full">
                {plan.id === 'enterprise' ? 'Contact sales' : 'Upgrade'}
              </Button>
            </div>
          {/if}
        </div>
      </Card>
    {/each}
  </div>
</div>
