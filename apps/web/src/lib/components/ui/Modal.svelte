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

  let { open = $bindable(false), onClose, title = '', children, footer }: ModalProps = $props();
</script>

<Dialog.Root
  bind:open
  onOpenChange={(o) => {
    if (!o) onClose();
  }}
>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-50 bg-black/50" />
    <Dialog.Content
      class="bg-light-bg border-light-border fixed z-50 border p-4 shadow-xl max-sm:inset-0 max-sm:max-w-none max-sm:rounded-none sm:top-1/2 sm:left-1/2 sm:w-full sm:max-w-lg sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-xl sm:p-6"
    >
      <Dialog.Title class="text-light-text mb-4 text-lg font-semibold">
        {title}
      </Dialog.Title>

      <button
        onclick={onClose}
        class="text-light-text-muted hover:text-light-text absolute top-4 right-4"
        aria-label="Close"
      >
        <X size={20} />
      </button>

      {@render children()}

      {#if footer}
        <div class="border-light-border mt-4 border-t pt-4">
          {@render footer()}
        </div>
      {/if}
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
