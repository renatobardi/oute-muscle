<script lang="ts">
  import type { Snippet } from 'svelte';

  interface PageHeaderProps {
    title: string;
    description?: string;
    actions?: Snippet;
  }

  let { title, description, actions }: PageHeaderProps = $props();
</script>

<div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
  <div>
    <h1 class="text-2xl font-bold text-light-text">{title}</h1>
    {#if description}
      <p class="text-sm text-light-text-secondary mt-1">{description}</p>
    {/if}
  </div>
  {#if actions}
    <div class="flex gap-2">
      {@render actions()}
    </div>
  {/if}
</div>
