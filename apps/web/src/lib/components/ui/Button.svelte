<script lang="ts">
  import type { Snippet } from 'svelte';
  import type { HTMLButtonAttributes } from 'svelte/elements';
  import { twMerge } from 'tailwind-merge';

  type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
  type Size = 'sm' | 'md' | 'lg';

  interface ButtonProps extends HTMLButtonAttributes {
    variant?: Variant;
    size?: Size;
    loading?: boolean;
    disabled?: boolean;
    type?: 'button' | 'submit' | 'reset';
    children: Snippet;
    class?: string;
  }

  // svelte-ignore custom_element_props_identifier
  let {
    variant = 'primary',
    size = 'md',
    loading = false,
    disabled = false,
    type = 'button',
    children,
    class: className,
    ...rest
  }: ButtonProps = $props();

  const sizeClasses: Record<Size, string> = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5',
    md: 'text-sm px-3.5 py-2 gap-2',
    lg: 'text-base px-4 py-2.5 gap-2',
  };

  const variantClasses: Record<Variant, string> = {
    primary: [
      'bg-primary-500 text-white',
      'hover:bg-primary-600',
      'focus-visible:outline-primary-500 focus-visible:outline-2 focus-visible:outline-offset-2',
      'active:bg-primary-600',
      'disabled:bg-primary-400 disabled:cursor-not-allowed disabled:opacity-50',
    ].join(' '),
    secondary: [
      'bg-light-bg border border-light-border text-light-text',
      'hover:bg-light-bg-hover',
      'focus-visible:outline-primary-500 focus-visible:outline-2 focus-visible:outline-offset-2',
      'active:bg-light-bg-hover',
      'disabled:opacity-50 disabled:cursor-not-allowed',
    ].join(' '),
    ghost: [
      'bg-transparent text-light-text-secondary',
      'hover:bg-light-bg-hover',
      'focus-visible:outline-primary-500 focus-visible:outline-2 focus-visible:outline-offset-2',
      'active:bg-light-bg-hover',
      'disabled:opacity-50 disabled:cursor-not-allowed',
    ].join(' '),
    danger: [
      'bg-error text-white',
      'hover:bg-error/90',
      'focus-visible:outline-error focus-visible:outline-2 focus-visible:outline-offset-2',
      'active:bg-error/80',
      'disabled:bg-error-light disabled:cursor-not-allowed disabled:opacity-50',
    ].join(' '),
  };

  const spinnerSizeClasses: Record<Size, string> = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  };

  let classes = $derived(
    twMerge(
      'inline-flex items-center justify-center font-medium rounded-md transition-colors focus-visible:outline',
      sizeClasses[size],
      variantClasses[variant],
      className,
    ),
  );
</script>

<button
  {type}
  class={classes}
  disabled={disabled || loading}
  aria-busy={loading}
  {...rest}
>
  {#if loading}
    <span
      class={twMerge(
        'animate-spin rounded-full border-2 border-current border-t-transparent',
        spinnerSizeClasses[size],
      )}
      aria-hidden="true"
    ></span>
  {/if}
  {@render children()}
</button>
