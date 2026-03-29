<script lang="ts">
  /**
   * T137: Dashboard group layout — sidebar navigation + top bar.
   * Rendered for all routes under (dashboard)/.
   */
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { auth, currentUser } from '$lib/stores/auth';
  import { isEnterprise as isPlanEnterprise } from '$lib/stores/tenant';

  let { children } = $props();

  const nav = [
    { href: '/incidents', label: 'Incidents', icon: '⚡' },
    { href: '/rules', label: 'Rules', icon: '🔒' },
    { href: '/scans', label: 'Scans', icon: '🔍' },
    { href: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  const enterpriseNav = [
    { href: '/audit', label: 'Audit Log', icon: '📋' },
    { href: '/rules/candidates', label: 'Rule Synthesis', icon: '✨' },
  ];

  function isActive(href: string): boolean {
    return $page.url.pathname.startsWith(href);
  }

  async function handleLogout() {
    auth.clearUser();
    await fetch('/api/auth/session', { method: 'DELETE' });
    await goto('/auth/login');
  }
</script>

<div class="flex h-screen bg-gray-50">
  <!-- Sidebar -->
  <aside class="flex w-64 flex-col border-r border-gray-200 bg-white">
    <!-- Logo -->
    <div class="flex h-16 items-center border-b border-gray-200 px-6">
      <span class="text-lg font-bold text-gray-900">Oute Muscle</span>
      <span class="ml-2 rounded bg-indigo-100 px-1.5 py-0.5 text-xs font-medium text-indigo-700"
        >β</span
      >
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto px-4 py-4">
      <ul class="space-y-1">
        {#each nav as item}
          <li>
            <a
              href={item.href}
              class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors
                {isActive(item.href)
                ? 'bg-indigo-50 text-indigo-700'
                : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'}"
            >
              <span>{item.icon}</span>
              {item.label}
            </a>
          </li>
        {/each}

        {#if $isPlanEnterprise}
          <li class="pt-4">
            <p class="px-3 pb-1 text-xs font-semibold tracking-wider text-gray-400 uppercase">
              Enterprise
            </p>
          </li>
          {#each enterpriseNav as item}
            <li>
              <a
                href={item.href}
                class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors
                  {isActive(item.href)
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'}"
              >
                <span>{item.icon}</span>
                {item.label}
              </a>
            </li>
          {/each}
        {/if}
      </ul>
    </nav>

    <!-- User footer -->
    <div class="border-t border-gray-200 p-4">
      <div class="flex items-center justify-between">
        <div class="min-w-0">
          <p class="truncate text-sm font-medium text-gray-900">{$currentUser?.email ?? ''}</p>
          <p class="text-xs text-gray-500 capitalize">{$currentUser?.role ?? ''}</p>
        </div>
        <button
          onclick={handleLogout}
          class="ml-2 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          title="Sign out"
          aria-label="Sign out"
        >
          ↪
        </button>
      </div>
    </div>
  </aside>

  <!-- Main content -->
  <main class="flex flex-1 flex-col overflow-hidden">
    <div class="flex-1 overflow-y-auto p-8">
      {@render children()}
    </div>
  </main>
</div>
