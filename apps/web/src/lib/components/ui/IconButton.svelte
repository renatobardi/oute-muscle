<script lang="ts">
  import type { Component } from 'svelte';
  import type { HTMLButtonAttributes } from 'svelte/elements';

  interface Props extends HTMLButtonAttributes {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    icon: any;
    label: string;
    variant?: 'ghost' | 'secondary';
    size?: 'sm' | 'md';
    disabled?: boolean;
  }

  let {
    icon,
    label,
    variant = 'ghost',
    size = 'md',
    disabled = false,
    ...rest
  }: Props = $props();

  const variantClasses: Record<string, string> = {
    ghost: 'text-light-text-secondary hover:bg-light-bg-hover hover:text-light-text',
    secondary: 'bg-light-bg border border-light-border text-light-text hover:bg-light-bg-hover',
  };

  const sizeClasses: Record<string, string> = {
    sm: 'h-8 w-8',
    md: 'h-9 w-9',
  };

  const iconSizes: Record<string, number> = {
    sm: 16,
    md: 18,
  };

  let iconSize = $derived(iconSizes[size]);
</script>

<button
  type="button"
  aria-label={label}
  {disabled}
  class="inline-flex items-center justify-center rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 {variantClasses[variant]} {sizeClasses[size]} {disabled ? 'opacity-50 cursor-not-allowed pointer-events-none' : ''}"
  {...rest}
>
  {#snippet iconRender()}
    {@const Icon = icon}
    <Icon size={iconSize} />
  {/snippet}
  {@render iconRender()}
</button>
