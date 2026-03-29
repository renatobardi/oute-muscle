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

<div class="flex min-h-screen items-center justify-center bg-dark-bg">
  <div class="w-full max-w-md p-4">
    <!-- Branding -->
    <div class="mb-8 text-center">
      <div class="inline-flex items-center gap-2 mb-2">
        <h1 class="text-2xl font-bold text-dark-text">Oute Muscle</h1>
        <span class="rounded bg-primary-500/20 px-1.5 py-0.5 text-xs font-medium text-primary-400">&beta;</span>
      </div>
    </div>

    <Card class="text-center">
      <div class="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-warning-light">
        <Clock class="h-8 w-8 text-warning" />
      </div>

      <h2 class="text-xl font-semibold text-light-text">Pending Approval</h2>
      <p class="mt-3 text-sm leading-relaxed text-light-text-secondary">
        Your account is pending approval. An administrator will assign you to a team.
      </p>

      <div class="mt-8">
        <Button variant="secondary" onclick={handleLogout} loading={loggingOut} disabled={loggingOut}>
          Sign out
        </Button>
      </div>
    </Card>
  </div>
</div>
