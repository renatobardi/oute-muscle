<script lang="ts">
  import type { Snippet } from 'svelte';
  import { twMerge } from 'tailwind-merge';

  interface CardProps {
    padding?: 'sm' | 'md' | 'lg';
    children: Snippet;
    header?: Snippet;
    class?: string;
  }

  const { padding = 'md', children, header, class: className }: CardProps = $props();

  const paddingMap: Record<string, string> = {
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };
</script>

<div
  class={twMerge(
    'bg-light-bg border-light-border rounded-xl border shadow-sm',
    paddingMap[padding],
    className
  )}
>
  {#if header}
    <div class="border-light-border mb-4 border-b pb-4">
      {@render header()}
    </div>
  {/if}
  {@render children()}
</div>
