<script lang="ts">
  import type { Snippet } from 'svelte';
  import { Dialog } from 'bits-ui';
  import { X } from 'lucide-svelte';

  interface ModalProps {
    open?: boolean;
    onClose: () => void;
    title?: string;
    children: Snippet;
    footer?: Snippet;
  }

  let {
    open = $bindable(false),
    onClose,
    title = '',
    children,
    footer,
  }: ModalProps = $props();
</script>

<Dialog.Root bind:open onOpenChange={(o) => { if (!o) onClose(); }}>
  <Dialog.Portal>
    <Dialog.Overlay
      class="fixed inset-0 z-50 bg-black/50"
    />
    <Dialog.Content
      class="fixed z-50 bg-light-bg shadow-xl border border-light-border p-4 sm:p-6 max-sm:inset-0 max-sm:rounded-none max-sm:max-w-none sm:left-1/2 sm:top-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2 sm:w-full sm:max-w-lg sm:rounded-xl"
    >
      <Dialog.Title class="text-lg font-semibold text-light-text mb-4">
        {title}
      </Dialog.Title>

      <button
        onclick={onClose}
        class="absolute top-4 right-4 text-light-text-muted hover:text-light-text"
        aria-label="Close"
      >
        <X size={20} />
      </button>

      {@render children()}

      {#if footer}
        <div class="border-t border-light-border pt-4 mt-4">
          {@render footer()}
        </div>
      {/if}
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
