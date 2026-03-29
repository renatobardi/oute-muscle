<script lang="ts">
  import ChevronDown from 'lucide-svelte/icons/chevron-down';

  export type SelectOption = {
    value: string;
    label: string;
  };

  interface SelectProps {
    label?: string;
    options: SelectOption[];
    value?: string;
    placeholder?: string;
    disabled?: boolean;
    onchange?: (value: string) => void;
  }

  let {
    label,
    options,
    value = '',
    placeholder = 'Select...',
    disabled = false,
    onchange,
  }: SelectProps = $props();

  let selectId = $derived(label ? `select-${label.toLowerCase().replace(/\s+/g, '-')}` : undefined);

  function handleChange(event: Event) {
    const target = event.target as HTMLSelectElement;
    onchange?.(target.value);
  }
</script>

<div>
  {#if label}
    <label for={selectId} class="block text-sm font-medium text-light-text mb-1.5">
      {label}
    </label>
  {/if}
  <div class="relative">
    <select
      id={selectId}
      class="w-full appearance-none rounded-lg border border-light-border-strong bg-light-bg text-light-text text-sm px-3 py-2.5 h-11 pr-10 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
      {disabled}
      onchange={handleChange}
    >
      <option value="" disabled selected={value === ''}>
        {placeholder}
      </option>
      {#each options as option (option.value)}
        <option value={option.value} selected={value === option.value}>
          {option.label}
        </option>
      {/each}
    </select>
    <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 text-light-text-secondary">
      <ChevronDown class="h-4 w-4" />
    </div>
  </div>
</div>
