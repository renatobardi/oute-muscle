<script lang="ts">
  interface Props {
    variant?: 'text' | 'card' | 'table-row' | 'circle';
    lines?: number;
    rows?: number;
  }

  let { variant = 'text', lines = 3, rows = 5 }: Props = $props();

  const textWidths = ['w-full', 'w-4/5', 'w-3/5'];
</script>

{#if variant === 'text'}
  <div class="space-y-3">
    {#each Array(lines) as _, i}
      <div class="bg-neutral-200 animate-pulse rounded h-4 {textWidths[i % textWidths.length]}"></div>
    {/each}
  </div>
{:else if variant === 'card'}
  <div class="bg-neutral-200 animate-pulse rounded-xl h-32 w-full"></div>
{:else if variant === 'table-row'}
  <div>
    {#each Array(rows) as _}
      <div class="flex items-center gap-4 h-10 border-b border-neutral-100">
        <div class="bg-neutral-200 animate-pulse rounded h-4 w-1/4"></div>
        <div class="bg-neutral-200 animate-pulse rounded h-4 w-2/5"></div>
        <div class="bg-neutral-200 animate-pulse rounded h-4 w-1/5"></div>
        <div class="bg-neutral-200 animate-pulse rounded h-4 w-1/6"></div>
      </div>
    {/each}
  </div>
{:else if variant === 'circle'}
  <div class="bg-neutral-200 animate-pulse rounded-full h-10 w-10"></div>
{/if}
