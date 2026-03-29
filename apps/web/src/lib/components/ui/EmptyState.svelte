<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    icon?: any;
    title: string;
    description?: string;
    action?: Snippet;
  }

  let { icon, title, description, action }: Props = $props();
</script>

<div class="flex flex-col items-center justify-center py-12 text-center">
  {#if icon}
    <div class="rounded-full bg-neutral-100 p-3 mb-4">
      {@render iconRender()}
    </div>
  {/if}
  <h3 class="text-lg font-semibold text-light-text">{title}</h3>
  {#if description}
    <p class="text-sm text-light-text-secondary mt-1 max-w-sm">{description}</p>
  {/if}
  {#if action}
    <div class="mt-4">
      {@render action()}
    </div>
  {/if}
</div>

{#snippet iconRender()}
  {#if icon}
    {@const Icon = icon}
    <Icon size={24} class="text-light-text-muted" />
  {/if}
{/snippet}
