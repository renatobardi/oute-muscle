import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import Modal from './Modal.svelte';
import { textSnippet } from './test-helpers';

describe('Modal', () => {
  const baseProps = {
    open: true,
    onClose: vi.fn(),
    title: 'Test Modal',
    children: textSnippet('Modal content'),
  };

  it('renders title when open', () => {
    render(Modal, { props: { ...baseProps } });
    expect(screen.getByText('Test Modal')).toBeTruthy();
  });

  it('renders children content when open', () => {
    render(Modal, { props: { ...baseProps } });
    expect(screen.getByText('Modal content')).toBeTruthy();
  });

  it('renders close button with aria-label', () => {
    render(Modal, { props: { ...baseProps } });
    expect(screen.getByLabelText('Close')).toBeTruthy();
  });

  it('calls onClose when close button is clicked', async () => {
    const onClose = vi.fn();
    render(Modal, { props: { ...baseProps, onClose } });
    await fireEvent.click(screen.getByLabelText('Close'));
    expect(onClose).toHaveBeenCalled();
  });

  it('does not render content when closed', () => {
    render(Modal, { props: { ...baseProps, open: false } });
    expect(screen.queryByText('Test Modal')).toBeNull();
  });

  it('renders footer when provided', () => {
    render(Modal, {
      props: {
        ...baseProps,
        footer: textSnippet('Footer content'),
      },
    });
    expect(screen.getByText('Footer content')).toBeTruthy();
  });
});
