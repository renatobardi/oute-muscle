import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import Button from './Button.svelte';

function textSnippet(text: string) {
  return createRawSnippet(() => ({
    render: () => `<span>${text}</span>`,
  }));
}

describe('Button', () => {
  it('renders children text', () => {
    render(Button, { props: { children: textSnippet('Click me') } });
    expect(screen.getByRole('button')).toHaveTextContent('Click me');
  });

  it('defaults to type="button"', () => {
    render(Button, { props: { children: textSnippet('Btn') } });
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button');
  });

  it('applies primary variant classes by default', () => {
    render(Button, { props: { children: textSnippet('Btn') } });
    expect(screen.getByRole('button').className).toContain('bg-primary-500');
  });

  it('applies danger variant classes', () => {
    render(Button, { props: { variant: 'danger', children: textSnippet('Btn') } });
    expect(screen.getByRole('button').className).toContain('bg-error');
  });

  it('applies ghost variant classes', () => {
    render(Button, { props: { variant: 'ghost', children: textSnippet('Btn') } });
    expect(screen.getByRole('button').className).toContain('bg-transparent');
  });

  it('applies secondary variant classes', () => {
    render(Button, { props: { variant: 'secondary', children: textSnippet('Btn') } });
    expect(screen.getByRole('button').className).toContain('border-light-border');
  });

  it('applies size classes', () => {
    render(Button, { props: { size: 'sm', children: textSnippet('Btn') } });
    expect(screen.getByRole('button').className).toContain('text-xs');
  });

  it('applies lg size classes', () => {
    render(Button, { props: { size: 'lg', children: textSnippet('Btn') } });
    expect(screen.getByRole('button').className).toContain('text-base');
  });

  it('is disabled when disabled=true', () => {
    render(Button, { props: { disabled: true, children: textSnippet('Btn') } });
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('is disabled when loading=true', () => {
    render(Button, { props: { loading: true, children: textSnippet('Btn') } });
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
  });

  it('shows spinner when loading', () => {
    render(Button, { props: { loading: true, children: textSnippet('Btn') } });
    const spinner = screen.getByRole('button').querySelector('[aria-hidden="true"]');
    expect(spinner).toBeTruthy();
    expect(spinner?.className).toContain('animate-spin');
  });

  it('fires click handler when clicked', async () => {
    const handleClick = vi.fn();
    render(Button, { props: { onclick: handleClick, children: textSnippet('Btn') } });
    await fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledOnce();
  });

  it('sets disabled attribute when disabled', () => {
    render(Button, {
      props: { disabled: true, children: textSnippet('Btn') },
    });
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
