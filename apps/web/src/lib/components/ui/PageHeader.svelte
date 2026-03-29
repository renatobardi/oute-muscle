<script lang="ts">
  import type { Snippet } from 'svelte';

  interface PageHeaderProps {
    title: string;
    description?: string;
    actions?: Snippet;
  }

  let { title, description, actions }: PageHeaderProps = $props();
</script>

<div class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
  <div>
    <h1 class="text-light-text text-2xl font-bold">{title}</h1>
    {#if description}
      <p class="text-light-text-secondary mt-1 text-sm">{description}</p>
    {/if}
  </div>
  {#if actions}
    <div class="flex gap-2">
      {@render actions()}
    </div>
  {/if}
</div>
