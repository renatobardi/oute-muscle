<script lang="ts">
  import { Sidebar } from '$components/ui';
  import { Home, Users, Building2, Activity, AlertTriangle, ShieldCheck, KeyRound } from 'lucide-svelte';

  let { children } = $props();

  const items = [
    { icon: Home, label: 'Overview', href: '/admin' },
    { icon: Users, label: 'Users', href: '/admin/users' },
    { icon: Building2, label: 'Tenants', href: '/admin/tenants' },
    { icon: Activity, label: 'Health', href: '/admin/health' },
    { icon: AlertTriangle, label: 'Incidents', href: '/admin/incidents' },
    { icon: ShieldCheck, label: 'Rules', href: '/admin/rules' },
    { icon: KeyRound, label: 'Access Control', href: '/admin/access' },
  ];

  async function handleLogout() {
    await fetch('/api/auth/session', { method: 'DELETE' });
    window.location.href = '/auth/login';
  }
</script>

<div class="flex h-screen">
  <Sidebar
    {items}
    variant="admin"
    user={{ email: 'admin@oute.pro', role: 'admin' }}
    onLogout={handleLogout}
  />
  <main class="flex flex-1 flex-col overflow-hidden bg-light-bg-page">
    <div class="flex-1 overflow-y-auto p-8 mt-14 md:mt-0">
      {@render children()}
    </div>
  </main>
</div>
