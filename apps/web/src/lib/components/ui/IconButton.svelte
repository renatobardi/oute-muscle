<script lang="ts">
  import type { HTMLButtonAttributes } from 'svelte/elements';

  interface Props extends HTMLButtonAttributes {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    icon: any;
    label: string;
    variant?: 'ghost' | 'secondary';
    size?: 'sm' | 'md';
    disabled?: boolean;
  }

  // svelte-ignore custom_element_props_identifier
  let { icon, label, variant = 'ghost', size = 'md', disabled = false, ...rest }: Props = $props();

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
  class="focus-visible:ring-primary-500 inline-flex items-center justify-center rounded-md transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none {variantClasses[
    variant
  ]} {sizeClasses[size]} {disabled ? 'pointer-events-none cursor-not-allowed opacity-50' : ''}"
  {...rest}
>
  {#snippet iconRender()}
    {@const Icon = icon}
    <Icon size={iconSize} />
  {/snippet}
  {@render iconRender()}
</button>
