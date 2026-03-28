/**
 * T140: Tenant context store — current tenant profile + plan limits.
 */

import { writable, derived } from 'svelte/store';
import type { Tenant } from '$lib/api/client';

interface TenantState {
  tenant: Tenant | null;
  loading: boolean;
  error: string | null;
}

function createTenantStore() {
  const { subscribe, set, update } = writable<TenantState>({
    tenant: null,
    loading: false,
    error: null,
  });

  return {
    subscribe,

    async load(fetcher: () => Promise<Tenant>) {
      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const tenant = await fetcher();
        set({ tenant, loading: false, error: null });
      } catch (e) {
        update((s) => ({
          ...s,
          loading: false,
          error: e instanceof Error ? e.message : 'Failed to load tenant',
        }));
      }
    },

    clear() {
      set({ tenant: null, loading: false, error: null });
    },
  };
}

export const tenantStore = createTenantStore();

// ---------------------------------------------------------------------------
// Derived plan helpers
// ---------------------------------------------------------------------------

export const currentPlan = derived(tenantStore, ($t) => $t.tenant?.plan ?? null);

export const isEnterprise = derived(tenantStore, ($t) => $t.tenant?.plan === 'enterprise');

export const isTeamOrAbove = derived(
  tenantStore,
  ($t) => $t.tenant?.plan === 'team' || $t.tenant?.plan === 'enterprise',
);
