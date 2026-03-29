<script lang="ts">
  import type { HTMLInputAttributes } from 'svelte/elements';
  import { AlertCircle } from 'lucide-svelte';
  import { twMerge } from 'tailwind-merge';

  interface InputProps extends HTMLInputAttributes {
    label?: string;
    type?: 'text' | 'email' | 'password' | 'search' | 'number';
    placeholder?: string;
    value?: string;
    error?: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    icon?: any;
    disabled?: boolean;
    class?: string;
  }

  // svelte-ignore custom_element_props_identifier
  let {
    label,
    type = 'text',
    placeholder = '',
    value = $bindable(''),
    error,
    icon,
    disabled = false,
    id,
    class: className,
    ...rest
  }: InputProps = $props();

  let inputId = $derived(
    id ?? (label ? `input-${label.toLowerCase().replace(/\s+/g, '-')}` : undefined)
  );

  let inputClasses = $derived(
    twMerge(
      'w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm transition h-11',
      'border-light-border-strong bg-light-bg text-light-text placeholder:text-light-text-muted',
      'focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none',
      error && 'border-error text-light-text focus:border-error focus:ring-2 focus:ring-error/20',
      disabled && 'opacity-50 cursor-not-allowed bg-neutral-50',
      icon && 'pl-10',
      className
    )
  );
</script>

<div>
  {#if label}
    <label for={inputId} class="text-light-text mb-1.5 block text-sm font-medium">
      {label}
    </label>
  {/if}

  <div class="relative">
    {#if icon}
      <div class="pointer-events-none absolute inset-y-0 left-3 flex items-center">
        {@render iconSlot()}
      </div>
    {/if}

    <input
      id={inputId}
      {type}
      {placeholder}
      {disabled}
      bind:value
      class={inputClasses}
      aria-invalid={error ? 'true' : undefined}
      {...rest}
    />
  </div>

  {#if error}
    <div class="text-error-text mt-1.5 flex items-center gap-1.5 text-xs">
      <AlertCircle size={14} aria-hidden="true" />
      <span>{error}</span>
    </div>
  {/if}
</div>

{#snippet iconSlot()}
  {#if icon}
    {@const Icon = icon}
    <Icon size={16} class="text-light-text-muted" />
  {/if}
{/snippet}
