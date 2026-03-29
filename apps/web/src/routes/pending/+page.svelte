<!--
  T019: Pending approval page.
  Shown to users who have no tenant assigned yet.
-->
<script lang="ts">
  import { Button, Card } from '$components/ui';
  import { Clock } from 'lucide-svelte';

  let loggingOut = $state(false);

  async function handleLogout() {
    loggingOut = true;
    try {
      await fetch('/api/auth/session', { method: 'DELETE' });
    } finally {
      window.location.href = '/auth/login';
    }
  }
</script>

<div class="bg-dark-bg flex min-h-screen items-center justify-center">
  <div class="w-full max-w-md p-4">
    <!-- Branding -->
    <div class="mb-8 text-center">
      <div class="mb-2 inline-flex items-center gap-2">
        <h1 class="text-dark-text text-2xl font-bold">Oute Muscle</h1>
        <span class="bg-primary-500/20 text-primary-400 rounded px-1.5 py-0.5 text-xs font-medium"
          >&beta;</span
        >
      </div>
    </div>

    <Card class="text-center">
      <div
        class="bg-warning-light mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full"
      >
        <Clock class="text-warning h-8 w-8" />
      </div>

      <h2 class="text-light-text text-xl font-semibold">Pending Approval</h2>
      <p class="text-light-text-secondary mt-3 text-sm leading-relaxed">
        Your account is pending approval. An administrator will assign you to a team.
      </p>

      <div class="mt-8">
        <Button
          variant="secondary"
          onclick={handleLogout}
          loading={loggingOut}
          disabled={loggingOut}
        >
          Sign out
        </Button>
      </div>
    </Card>
  </div>
</div>
