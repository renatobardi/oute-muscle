import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import Table from './Table.svelte';
import type { TableColumn } from './Table.svelte';

const columns: TableColumn[] = [
  { key: 'name', label: 'Name', sortable: true },
  { key: 'status', label: 'Status' },
  { key: 'count', label: 'Count', align: 'right' },
];

const data = [
  { name: 'Alpha', status: 'active', count: 10 },
  { name: 'Beta', status: 'inactive', count: 20 },
];

describe('Table', () => {
  describe('rendering data', () => {
    it('renders column headers', () => {
      render(Table, { props: { columns, data } });
      expect(screen.getByText('Name')).toBeTruthy();
      expect(screen.getByText('Status')).toBeTruthy();
      expect(screen.getByText('Count')).toBeTruthy();
    });

    it('renders data rows', () => {
      render(Table, { props: { columns, data } });
      expect(screen.getByText('Alpha')).toBeTruthy();
      expect(screen.getByText('Beta')).toBeTruthy();
      expect(screen.getByText('10')).toBeTruthy();
      expect(screen.getByText('20')).toBeTruthy();
    });
  });

  describe('empty state', () => {
    it('shows EmptyState when data is empty', () => {
      render(Table, {
        props: { columns, data: [], emptyTitle: 'No incidents found' },
      });
      expect(screen.getByText('No incidents found')).toBeTruthy();
    });

    it('shows default empty title', () => {
      render(Table, { props: { columns, data: [] } });
      expect(screen.getByText('No data')).toBeTruthy();
    });
  });

  describe('loading state', () => {
    it('renders skeleton rows when loading', () => {
      const { container } = render(Table, {
        props: { columns, loading: true, skeletonRows: 3 },
      });
      const skeletonRows = container.querySelectorAll('tbody tr');
      expect(skeletonRows.length).toBe(3);
    });

    it('does not show data when loading', () => {
      render(Table, { props: { columns, data, loading: true } });
      expect(screen.queryByText('Alpha')).toBeNull();
    });
  });

  describe('sorting', () => {
    it('calls onSort when sortable header is clicked', async () => {
      const onSort = vi.fn();
      render(Table, {
        props: { columns, data, onSort, sortKey: 'name', sortDir: 'asc' },
      });
      await fireEvent.click(screen.getByText('Name'));
      expect(onSort).toHaveBeenCalledWith('name');
    });

    it('does not call onSort for non-sortable columns', async () => {
      const onSort = vi.fn();
      render(Table, {
        props: { columns, data, onSort },
      });
      await fireEvent.click(screen.getByText('Status'));
      expect(onSort).not.toHaveBeenCalled();
    });

    it('shows sort indicator on active sort column', () => {
      const { container } = render(Table, {
        props: { columns, data, onSort: vi.fn(), sortKey: 'name', sortDir: 'asc' },
      });
      // ChevronUp SVG should be present for asc sort
      const svg = container.querySelector('th svg');
      expect(svg).toBeTruthy();
    });
  });

  describe('column alignment', () => {
    it('applies right alignment class to right-aligned columns', () => {
      const { container } = render(Table, { props: { columns, data } });
      const headerCells = container.querySelectorAll('th');
      const countHeader = Array.from(headerCells).find((th) =>
        th.textContent?.includes('Count')
      );
      expect(countHeader?.className).toContain('text-right');
    });
  });
});
