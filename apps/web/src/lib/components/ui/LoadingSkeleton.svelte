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
      <div
        class="h-4 animate-pulse rounded bg-neutral-200 {textWidths[i % textWidths.length]}"
      ></div>
    {/each}
  </div>
{:else if variant === 'card'}
  <div class="h-32 w-full animate-pulse rounded-xl bg-neutral-200"></div>
{:else if variant === 'table-row'}
  <div>
    {#each Array(rows) as _}
      <div class="flex h-10 items-center gap-4 border-b border-neutral-100">
        <div class="h-4 w-1/4 animate-pulse rounded bg-neutral-200"></div>
        <div class="h-4 w-2/5 animate-pulse rounded bg-neutral-200"></div>
        <div class="h-4 w-1/5 animate-pulse rounded bg-neutral-200"></div>
        <div class="h-4 w-1/6 animate-pulse rounded bg-neutral-200"></div>
      </div>
    {/each}
  </div>
{:else if variant === 'circle'}
  <div class="h-10 w-10 animate-pulse rounded-full bg-neutral-200"></div>
{/if}
