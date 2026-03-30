import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import Badge from './Badge.svelte';

describe('Badge', () => {
  describe('severity auto-mapping', () => {
    it('renders severity label and applies severity classes', () => {
      render(Badge, { props: { severity: 'critical' } });
      const badge = screen.getByText('critical');
      expect(badge.className).toContain('bg-severity-critical-light');
      expect(badge.className).toContain('text-severity-critical-text');
    });

    it.each(['critical', 'high', 'medium', 'low', 'info'] as const)(
      'maps severity "%s" to correct token classes',
      (severity) => {
        render(Badge, { props: { severity } });
        const badge = screen.getByText(severity);
        expect(badge.className).toContain(`bg-severity-${severity}-light`);
        expect(badge.className).toContain(`text-severity-${severity}-text`);
      }
    );
  });

  describe('status auto-mapping', () => {
    it.each(['active', 'inactive', 'pending', 'failed', 'running'] as const)(
      'maps status "%s" to correct token classes',
      (status) => {
        render(Badge, { props: { status } });
        const badge = screen.getByText(status);
        expect(badge.className).toContain(`bg-status-${status}-light`);
        expect(badge.className).toContain(`text-status-${status}-text`);
      }
    );
  });

  describe('fallback behavior', () => {
    it('renders neutral classes when no severity or status', () => {
      render(Badge, { props: { label: 'unknown' } });
      const badge = screen.getByText('unknown');
      expect(badge.className).toContain('bg-neutral-100');
      expect(badge.className).toContain('text-neutral-700');
    });

    it('renders neutral when severity is unknown value', () => {
      // @ts-expect-error testing invalid value
      render(Badge, { props: { severity: 'nonexistent' } });
      const badge = screen.getByText('nonexistent');
      expect(badge.className).toContain('bg-neutral-100');
    });
  });

  describe('dot indicator', () => {
    it('shows dot by default', () => {
      const { container } = render(Badge, { props: { severity: 'high' } });
      const dot = container.querySelector('.h-1\\.5.w-1\\.5.rounded-full');
      expect(dot).toBeTruthy();
    });

    it('hides dot when dot=false', () => {
      const { container } = render(Badge, { props: { severity: 'high', dot: false } });
      const dot = container.querySelector('.h-1\\.5.w-1\\.5.rounded-full');
      expect(dot).toBeNull();
    });
  });

  describe('label override', () => {
    it('uses label prop over severity value', () => {
      render(Badge, { props: { severity: 'critical', label: 'Custom' } });
      expect(screen.getByText('Custom')).toBeTruthy();
      expect(screen.queryByText('critical')).toBeNull();
    });
  });

  describe('severity takes precedence over status', () => {
    it('uses severity colors when both provided', () => {
      render(Badge, { props: { severity: 'critical', status: 'active' } });
      const badge = screen.getByText('critical');
      expect(badge.className).toContain('bg-severity-critical-light');
      expect(badge.className).not.toContain('bg-status-active-light');
    });
  });
});
