import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import { Circle } from 'lucide-svelte';

// Mock $app/stores before importing Sidebar
vi.mock('$app/stores', async () => {
  const { readable } = await import('svelte/store');
  return {
    page: readable({
      url: new URL('http://localhost/incidents'),
      params: {},
    }),
  };
});

import Sidebar from './Sidebar.svelte';

const defaultItems = [
  { icon: Circle, label: 'Incidents', href: '/incidents' },
  { icon: Circle, label: 'Rules', href: '/rules' },
  { icon: Circle, label: 'Scans', href: '/scans' },
];

const defaultUser = {
  email: 'renato@oute.pro',
  role: 'admin',
};

describe('Sidebar', () => {
  let onLogout: () => void;

  beforeEach(() => {
    onLogout = vi.fn() as unknown as () => void;
  });

  describe('rendering items', () => {
    it('renders all navigation items', () => {
      render(Sidebar, { props: { items: defaultItems, user: defaultUser, onLogout } });
      expect(screen.getByText('Incidents')).toBeTruthy();
      expect(screen.getByText('Rules')).toBeTruthy();
      expect(screen.getByText('Scans')).toBeTruthy();
    });

    it('renders items as links with correct href', () => {
      render(Sidebar, { props: { items: defaultItems, user: defaultUser, onLogout } });
      const link = screen.getByText('Incidents').closest('a');
      expect(link).toHaveAttribute('href', '/incidents');
    });
  });

  describe('user footer', () => {
    it('renders user email', () => {
      render(Sidebar, { props: { items: defaultItems, user: defaultUser, onLogout } });
      expect(screen.getByText('renato@oute.pro')).toBeTruthy();
    });

    it('renders user initial as avatar', () => {
      render(Sidebar, { props: { items: defaultItems, user: defaultUser, onLogout } });
      expect(screen.getByText('R')).toBeTruthy();
    });

    it('renders role badge', () => {
      render(Sidebar, { props: { items: defaultItems, user: defaultUser, onLogout } });
      expect(screen.getByText('admin')).toBeTruthy();
    });

    it('calls onLogout when sign out is clicked', async () => {
      render(Sidebar, { props: { items: defaultItems, user: defaultUser, onLogout } });
      await fireEvent.click(screen.getByLabelText('Sign out'));
      expect(onLogout).toHaveBeenCalledOnce();
    });
  });

  describe('admin variant', () => {
    it('shows Admin badge when variant="admin"', () => {
      render(Sidebar, {
        props: { items: defaultItems, user: defaultUser, onLogout, variant: 'admin' },
      });
      expect(screen.getByText('Admin')).toBeTruthy();
    });

    it('does not show Admin badge by default', () => {
      render(Sidebar, { props: { items: defaultItems, user: defaultUser, onLogout } });
      expect(screen.queryByText('Admin')).toBeNull();
    });
  });

  describe('branding', () => {
    it('renders Oute Muscle brand name', () => {
      render(Sidebar, { props: { items: defaultItems, user: defaultUser, onLogout } });
      const brandElements = screen.getAllByText('Oute Muscle');
      expect(brandElements.length).toBeGreaterThan(0);
    });

    it('renders beta badge', () => {
      render(Sidebar, { props: { items: defaultItems, user: defaultUser, onLogout } });
      expect(screen.getByText('beta')).toBeTruthy();
    });
  });

  describe('mobile toggle', () => {
    it('renders hamburger button for mobile', () => {
      render(Sidebar, { props: { items: defaultItems, user: defaultUser, onLogout } });
      expect(screen.getByLabelText('Open menu')).toBeTruthy();
    });
  });
});
