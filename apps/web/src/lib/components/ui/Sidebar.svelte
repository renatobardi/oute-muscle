<script lang="ts">
  import { page } from '$app/stores';
  import { Menu, X, LogOut } from 'lucide-svelte';
  import Badge from './Badge.svelte';

  interface SidebarItem {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    icon: any;
    label: string;
    href: string;
    badge?: string;
  }

  interface SidebarUser {
    email: string;
    role: string;
    displayName?: string;
  }

  interface SidebarProps {
    items: SidebarItem[];
    variant?: 'default' | 'admin';
    user: SidebarUser;
    onLogout: () => void;
    enterpriseItems?: SidebarItem[];
    showEnterprise?: boolean;
  }

  let {
    items,
    variant = 'default',
    user,
    onLogout,
    enterpriseItems = [],
    showEnterprise = false,
  }: SidebarProps = $props();

  let mobileOpen = $state(false);

  function isActive(href: string): boolean {
    if (href === '/admin') return $page.url.pathname === '/admin';
    return $page.url.pathname.startsWith(href);
  }

  function handleNavClick() {
    mobileOpen = false;
  }
</script>

{#snippet navItem(item: SidebarItem)}
  {@const Icon = item.icon}
  <li>
    <a
      href={item.href}
      onclick={handleNavClick}
      class="flex items-center gap-3 rounded-r-md px-3 py-2 text-sm font-medium transition-colors
        {isActive(item.href)
        ? 'border-l-3 border-primary-500 bg-dark-bg-active text-dark-text pl-2.5'
        : 'text-dark-text-muted hover:bg-dark-bg-hover hover:text-dark-text pl-3'}"
    >
      <Icon size={20} />
      {item.label}
      {#if item.badge}
        <span class="ml-auto text-xs text-dark-text-muted">{item.badge}</span>
      {/if}
    </a>
  </li>
{/snippet}

<!-- Mobile top bar -->
<div class="fixed top-0 left-0 right-0 z-40 flex h-14 items-center border-b border-dark-border bg-dark-bg px-4 md:hidden">
  <button
    onclick={() => (mobileOpen = true)}
    class="text-dark-text-muted hover:text-dark-text"
    aria-label="Open menu"
  >
    <Menu size={24} />
  </button>
  <span class="ml-3 text-lg font-bold text-dark-text">Oute Muscle</span>
</div>

<!-- Mobile backdrop -->
{#if mobileOpen}
  <button
    class="fixed inset-0 z-40 bg-black/50 md:hidden"
    onclick={() => (mobileOpen = false)}
    aria-label="Close menu"
    tabindex="-1"
  ></button>
{/if}

<!-- Sidebar -->
<aside
  class="flex w-sidebar flex-col border-r border-dark-border bg-dark-bg
    {mobileOpen ? 'fixed inset-y-0 left-0 z-50' : 'hidden'} md:relative md:flex"
>
  <!-- Logo -->
  <div class="flex h-14 items-center gap-2 border-b border-dark-border px-4">
    <!-- Mobile close button -->
    <button
      class="text-dark-text-muted hover:text-dark-text md:hidden"
      onclick={() => (mobileOpen = false)}
      aria-label="Close menu"
    >
      <X size={20} />
    </button>
    <span class="text-lg font-bold text-dark-text">Oute Muscle</span>
    <span class="rounded bg-primary-500/20 px-1.5 py-0.5 text-xs text-primary-400">beta</span>
    {#if variant === 'admin'}
      <span class="rounded bg-error/20 px-1.5 py-0.5 text-xs text-error">Admin</span>
    {/if}
  </div>

  <!-- Navigation -->
  <nav class="flex-1 overflow-y-auto py-4">
    <ul class="space-y-1">
      {#each items as item}
        {@render navItem(item)}
      {/each}

      {#if showEnterprise && enterpriseItems && enterpriseItems.length > 0}
        <li class="px-3 pt-6 pb-1">
          <p class="text-xs font-semibold tracking-wider text-dark-text-dimmed uppercase">
            Enterprise
          </p>
        </li>
        {#each enterpriseItems as item}
          {@render navItem(item)}
        {/each}
      {/if}
    </ul>
  </nav>

  <!-- User footer -->
  <div class="border-t border-dark-border p-4">
    <div class="flex items-center gap-3">
      <div class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary-500/20 text-sm font-medium text-primary-400">
        {user.email.charAt(0).toUpperCase()}
      </div>
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm text-dark-text">{user.email}</p>
        <Badge label={user.role} dot={false} />
      </div>
      <button
        onclick={onLogout}
        class="flex-shrink-0 text-dark-text-muted hover:text-dark-text"
        title="Sign out"
        aria-label="Sign out"
      >
        <LogOut size={16} />
      </button>
    </div>
  </div>
</aside>
