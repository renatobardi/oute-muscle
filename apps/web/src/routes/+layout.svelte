<script lang="ts">
  /**
   * T137: Root layout with auth guard.
   * Public routes (/auth/*) bypass the guard.
   * All others redirect to /auth/login if unauthenticated.
   */
  import '../app.css';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { isAuthenticated } from '$lib/stores/auth';
  import { tenantStore } from '$lib/stores/tenant';
  import { apiClient } from '$lib/api';

  let { children } = $props();

  const PUBLIC_PATHS = ['/', '/auth/login', '/auth/callback', '/auth/register'];

  onMount(() => {
    const unsubscribe = isAuthenticated.subscribe(async (authed) => {
      const path = $page.url.pathname;
      const isPublic = PUBLIC_PATHS.some((p) => path.startsWith(p));

      if (!authed && !isPublic) {
        await goto('/auth/login');
        return;
      }

      if (authed && !$tenantStore.tenant && !$tenantStore.loading) {
        await tenantStore.load(() => apiClient.tenants.me());
      }
    });

    return unsubscribe;
  });
</script>

{@render children()}
