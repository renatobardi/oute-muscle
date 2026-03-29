<script lang="ts">
  import { goto } from '$app/navigation';
  import { auth, currentUser } from '$lib/stores/auth';
  import { isEnterprise as isPlanEnterprise } from '$lib/stores/tenant';
  import { Sidebar } from '$components/ui';
  import { Zap, Shield, ScanSearch, Settings, ScrollText, Sparkles } from 'lucide-svelte';

  let { children } = $props();

  const items = [
    { icon: Zap, label: 'Incidents', href: '/incidents' },
    { icon: Shield, label: 'Rules', href: '/rules' },
    { icon: ScanSearch, label: 'Scans', href: '/scans' },
    { icon: Settings, label: 'Settings', href: '/settings' },
  ];

  const enterpriseItems = [
    { icon: ScrollText, label: 'Audit Log', href: '/audit' },
    { icon: Sparkles, label: 'Rule Synthesis', href: '/rules/candidates' },
  ];

  async function handleLogout() {
    auth.clearUser();
    await fetch('/api/auth/session', { method: 'DELETE' });
    await goto('/auth/login');
  }
</script>

<div class="flex h-screen">
  <Sidebar
    {items}
    user={{ email: $currentUser?.email ?? '', role: $currentUser?.role ?? '' }}
    onLogout={handleLogout}
    {enterpriseItems}
    showEnterprise={$isPlanEnterprise}
  />
  <main class="flex flex-1 flex-col overflow-hidden bg-light-bg-page">
    <div class="flex-1 overflow-y-auto p-8 md:ml-0 mt-14 md:mt-0">
      {@render children()}
    </div>
  </main>
</div>
