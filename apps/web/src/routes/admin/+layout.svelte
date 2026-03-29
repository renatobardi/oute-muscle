<script lang="ts">
  /**
   * T045: Admin cockpit layout — dark sidebar + light content area.
   */
  import { page } from '$app/stores';

  let { children } = $props();

  const nav = [
    { href: '/admin', label: 'Overview', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1' },
    { href: '/admin/users', label: 'Users', icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197' },
    { href: '/admin/tenants', label: 'Tenants', icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4' },
    { href: '/admin/health', label: 'Health', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
    { href: '/admin/incidents', label: 'Incidents', icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z' },
    { href: '/admin/rules', label: 'Rules', icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z' },
    { href: '/admin/access', label: 'Access Control', icon: 'M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z' },
  ];

  function isActive(href: string): boolean {
    if (href === '/admin') {
      return $page.url.pathname === '/admin';
    }
    return $page.url.pathname.startsWith(href);
  }
</script>

<div class="flex h-screen bg-gray-50">
  <!-- Sidebar -->
  <aside class="flex w-64 flex-col bg-gray-900">
    <!-- Logo -->
    <div class="flex h-16 items-center border-b border-gray-700 px-6">
      <span class="text-lg font-bold text-white">Oute Muscle</span>
      <span class="ml-2 rounded bg-red-600 px-1.5 py-0.5 text-xs font-medium text-white">Admin</span>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto px-3 py-4">
      <ul class="space-y-1">
        {#each nav as item}
          <li>
            <a
              href={item.href}
              class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors
                {isActive(item.href)
                ? 'bg-gray-800 text-white'
                : 'text-gray-300 hover:bg-gray-800 hover:text-white'}"
            >
              <svg
                class="h-5 w-5 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="1.5"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d={item.icon} />
              </svg>
              {item.label}
            </a>
          </li>
        {/each}
      </ul>
    </nav>

    <!-- Back to dashboard -->
    <div class="border-t border-gray-700 p-4">
      <a
        href="/"
        class="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
      >
        <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Back to Dashboard
      </a>
    </div>
  </aside>

  <!-- Main content -->
  <main class="flex flex-1 flex-col overflow-hidden">
    <div class="flex-1 overflow-y-auto p-8">
      {@render children()}
    </div>
  </main>
</div>
