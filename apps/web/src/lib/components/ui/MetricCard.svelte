<script lang="ts">
  import type { Snippet } from 'svelte';
  import { TrendingUp, TrendingDown, Minus } from 'lucide-svelte';

  interface MetricCardProps {
    label: string;
    value: string | number;
    trend?: 'up' | 'down' | 'neutral';
    trendValue?: string;
    highlight?: boolean;
    children?: Snippet;
  }

  const {
    label,
    value,
    trend,
    trendValue,
    highlight = false,
    children,
  }: MetricCardProps = $props();

  const borderClass = $derived(
    highlight
      ? 'border-2 border-primary-500'
      : 'border border-light-border'
  );
</script>

<div class="bg-light-bg rounded-xl shadow-sm p-6 {borderClass}">
  <p class="text-sm font-medium text-light-text-secondary">{label}</p>
  <p class="text-2xl font-bold text-light-text mt-1">{value}</p>

  {#if trend}
    <div class="flex items-center gap-1 mt-2 text-sm">
      {#if trend === 'up'}
        <span class="text-success-text"><TrendingUp size={16} /></span>
      {:else if trend === 'down'}
        <span class="text-error-text"><TrendingDown size={16} /></span>
      {:else}
        <span class="text-light-text-muted"><Minus size={16} /></span>
      {/if}
      {#if trendValue}
        <span
          class={trend === 'up'
            ? 'text-success-text'
            : trend === 'down'
              ? 'text-error-text'
              : 'text-light-text-muted'}
        >
          {trendValue}
        </span>
      {/if}
    </div>
  {/if}

  {#if children}
    {@render children()}
  {/if}
</div>
