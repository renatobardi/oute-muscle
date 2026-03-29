<script lang="ts" module>
  export interface TableColumn {
    key: string;
    label: string;
    sortable?: boolean;
    align?: 'left' | 'center' | 'right';
    width?: string;
  }
</script>

<script lang="ts">
  import type { Snippet } from 'svelte';
  import { ChevronUp, ChevronDown } from 'lucide-svelte';
  import EmptyState from './EmptyState.svelte';
  import LoadingSkeleton from './LoadingSkeleton.svelte';

  interface TableProps {
    columns: TableColumn[];
    data?: Record<string, unknown>[];
    loading?: boolean;
    skeletonRows?: number;
    emptyTitle?: string;
    emptyDescription?: string;
    emptyAction?: Snippet;
    sortKey?: string;
    sortDir?: 'asc' | 'desc';
    onSort?: (key: string) => void;
    row?: Snippet<[Record<string, unknown>]>;
  }

  let {
    columns,
    data = [],
    loading = false,
    skeletonRows = 5,
    emptyTitle = 'No data',
    emptyDescription = '',
    emptyAction,
    sortKey,
    sortDir = 'asc',
    onSort,
    row,
  }: TableProps = $props();

  function alignClass(align?: 'left' | 'center' | 'right'): string {
    if (align === 'right') return 'text-right';
    if (align === 'center') return 'text-center';
    return 'text-left';
  }
</script>

<div class="overflow-x-auto">
  <table class="w-full text-sm">
    <thead>
      <tr class="border-light-border border-b">
        {#each columns as column}
          <th
            class="text-light-text-secondary px-4 py-3 text-xs font-semibold tracking-wider uppercase {alignClass(
              column.align
            )}
              {column.sortable && onSort ? 'hover:text-light-text cursor-pointer' : ''}"
            style={column.width ? `width: ${column.width}` : undefined}
            onclick={column.sortable && onSort ? () => onSort(column.key) : undefined}
          >
            <span class="inline-flex items-center gap-1">
              {column.label}
              {#if column.sortable && onSort && sortKey === column.key}
                {#if sortDir === 'asc'}
                  <ChevronUp size={14} />
                {:else}
                  <ChevronDown size={14} />
                {/if}
              {/if}
            </span>
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#if loading}
        {#each Array(skeletonRows) as _}
          <tr class="border-light-border border-b">
            {#each columns as column}
              <td class="px-4 py-3 {alignClass(column.align)}">
                <LoadingSkeleton variant="text" lines={1} />
              </td>
            {/each}
          </tr>
        {/each}
      {:else if data.length === 0}
        <tr>
          <td colspan={columns.length}>
            <EmptyState title={emptyTitle} description={emptyDescription} action={emptyAction} />
          </td>
        </tr>
      {:else if row}
        {#each data as item}
          {@render row(item)}
        {/each}
      {:else}
        {#each data as item}
          <tr class="border-light-border hover:bg-light-bg-hover border-b transition-colors">
            {#each columns as column}
              <td
                class="text-light-text px-4 py-3 {column.align === 'right'
                  ? 'text-right font-mono'
                  : ''} {column.align === 'center' ? 'text-center' : ''}"
              >
                <span class="block max-w-xs truncate" title={String(item[column.key] ?? '')}>
                  {String(item[column.key] ?? '')}
                </span>
              </td>
            {/each}
          </tr>
        {/each}
      {/if}
    </tbody>
  </table>
</div>
