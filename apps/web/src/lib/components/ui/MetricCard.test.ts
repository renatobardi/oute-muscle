import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import MetricCard from './MetricCard.svelte';

describe('MetricCard', () => {
  describe('basic rendering', () => {
    it('renders label and value', () => {
      render(MetricCard, { props: { label: 'Total Users', value: 1234 } });
      expect(screen.getByText('Total Users')).toBeTruthy();
      expect(screen.getByText('1234')).toBeTruthy();
    });

    it('renders string value', () => {
      render(MetricCard, { props: { label: 'Status', value: 'OK' } });
      expect(screen.getByText('OK')).toBeTruthy();
    });
  });

  describe('trend indicator', () => {
    it('renders up trend with success color', () => {
      const { container } = render(MetricCard, {
        props: { label: 'Users', value: 100, trend: 'up', trendValue: '+12%' },
      });
      expect(screen.getByText('+12%')).toBeTruthy();
      const trendSpan = container.querySelector('.text-success-text');
      expect(trendSpan).toBeTruthy();
    });

    it('renders down trend with error color', () => {
      const { container } = render(MetricCard, {
        props: { label: 'Users', value: 100, trend: 'down', trendValue: '-5%' },
      });
      expect(screen.getByText('-5%')).toBeTruthy();
      const trendSpan = container.querySelector('.text-error-text');
      expect(trendSpan).toBeTruthy();
    });

    it('renders neutral trend with muted color', () => {
      const { container } = render(MetricCard, {
        props: { label: 'Users', value: 100, trend: 'neutral', trendValue: '0%' },
      });
      expect(screen.getByText('0%')).toBeTruthy();
      const trendSpan = container.querySelector('.text-light-text-muted');
      expect(trendSpan).toBeTruthy();
    });

    it('does not render trend section when trend is undefined', () => {
      const { container } = render(MetricCard, {
        props: { label: 'Users', value: 100 },
      });
      // No TrendingUp/Down/Minus SVG should be present
      expect(container.querySelector('svg')).toBeNull();
    });
  });

  describe('highlight variant', () => {
    it('applies primary border when highlight=true', () => {
      const { container } = render(MetricCard, {
        props: { label: 'Alert', value: 5, highlight: true },
      });
      const card = container.firstElementChild as HTMLElement;
      expect(card.className).toContain('border-primary-500');
      expect(card.className).toContain('border-2');
    });

    it('applies normal border when highlight=false', () => {
      const { container } = render(MetricCard, {
        props: { label: 'Normal', value: 5 },
      });
      const card = container.firstElementChild as HTMLElement;
      expect(card.className).toContain('border-light-border');
      expect(card.className).not.toContain('border-primary-500');
    });
  });
});
