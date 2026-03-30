import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import Input from './Input.svelte';

describe('Input', () => {
  describe('basic rendering', () => {
    it('renders an input element', () => {
      render(Input);
      expect(screen.getByRole('textbox')).toBeTruthy();
    });

    it('renders with placeholder', () => {
      render(Input, { props: { placeholder: 'Enter text...' } });
      expect(screen.getByPlaceholderText('Enter text...')).toBeTruthy();
    });

    it('defaults to type="text"', () => {
      render(Input);
      expect(screen.getByRole('textbox')).toHaveAttribute('type', 'text');
    });
  });

  describe('label', () => {
    it('renders label when provided', () => {
      render(Input, { props: { label: 'Email' } });
      expect(screen.getByLabelText('Email')).toBeTruthy();
    });

    it('generates id from label for association', () => {
      render(Input, { props: { label: 'Email Address' } });
      const input = screen.getByLabelText('Email Address');
      expect(input.id).toBe('input-email-address');
    });

    it('uses explicit id over generated one', () => {
      render(Input, { props: { label: 'Email', id: 'my-email' } });
      const input = screen.getByLabelText('Email');
      expect(input.id).toBe('my-email');
    });
  });

  describe('error state', () => {
    it('shows error message when error prop is set', () => {
      render(Input, { props: { error: 'This field is required' } });
      expect(screen.getByText('This field is required')).toBeTruthy();
    });

    it('sets aria-invalid when error is present', () => {
      render(Input, { props: { error: 'Invalid' } });
      expect(screen.getByRole('textbox')).toHaveAttribute('aria-invalid', 'true');
    });

    it('does not set aria-invalid when no error', () => {
      render(Input);
      expect(screen.getByRole('textbox')).not.toHaveAttribute('aria-invalid');
    });

    it('applies error border classes', () => {
      render(Input, { props: { error: 'Error' } });
      expect(screen.getByRole('textbox').className).toContain('border-error');
    });
  });

  describe('icon prefix', () => {
    it('applies padding-left class when icon is provided', async () => {
      // Import a real lucide icon to test icon rendering
      const { Mail } = await import('lucide-svelte');
      render(Input, { props: { icon: Mail } });
      expect(screen.getByRole('textbox').className).toContain('pl-10');
    });
  });

  describe('disabled state', () => {
    it('disables input when disabled=true', () => {
      render(Input, { props: { disabled: true } });
      expect(screen.getByRole('textbox')).toBeDisabled();
    });

    it('applies disabled classes', () => {
      render(Input, { props: { disabled: true } });
      expect(screen.getByRole('textbox').className).toContain('opacity-50');
    });
  });
});
