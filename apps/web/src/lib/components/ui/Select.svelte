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
    <label for={selectId} class="text-light-text mb-1.5 block text-sm font-medium">
      {label}
    </label>
  {/if}
  <div class="relative">
    <select
      id={selectId}
      class="border-light-border-strong bg-light-bg text-light-text focus:border-primary-500 focus:ring-primary-500/20 h-11 w-full appearance-none rounded-lg border px-3 py-2.5 pr-10 text-sm focus:ring-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
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
    <div
      class="text-light-text-secondary pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3"
    >
      <ChevronDown class="h-4 w-4" />
    </div>
  </div>
</div>
