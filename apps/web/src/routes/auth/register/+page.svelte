<script lang="ts">
  /**
   * T138: Register page — workspace registration (new tenant sign-up).
   * Collects company name + user email, then starts OAuth flow.
   */
  import { goto } from '$app/navigation';
  import { Button, Input, Card } from '$components/ui';
  import { Building2, Mail } from 'lucide-svelte';

  let companyName = $state('');
  let email = $state('');
  let submitting = $state(false);
  let error = $state<string | null>(null);

  const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'https://muscle.oute.pro/api/v1';

  async function handleRegister(e: SubmitEvent) {
    e.preventDefault();
    submitting = true;
    error = null;

    try {
      const response = await fetch(`${API_BASE}/tenants/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company_name: companyName, admin_email: email }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error ?? `Registration failed (${response.status})`);
      }

      // Redirect to login to complete OAuth flow
      await goto('/auth/login');
    } catch (e_) {
      error = e_ instanceof Error ? e_.message : 'Registration failed';
    } finally {
      submitting = false;
    }
  }
</script>

<div class="flex min-h-screen items-center justify-center bg-dark-bg">
  <div class="w-full max-w-sm p-4">
    <!-- Branding -->
    <div class="mb-8 text-center">
      <div class="inline-flex items-center gap-2 mb-2">
        <h1 class="text-2xl font-bold text-dark-text">Oute Muscle</h1>
        <span class="rounded bg-primary-500/20 px-1.5 py-0.5 text-xs font-medium text-primary-400">&beta;</span>
      </div>
      <p class="text-sm text-dark-text-muted">Create your workspace</p>
    </div>

    <Card>
      {#if error}
        <div class="mb-4 flex items-center gap-2 rounded-lg bg-error-light border border-error-border p-3 text-sm text-error-text" role="alert">
          <svg class="h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {error}
        </div>
      {/if}

      <form onsubmit={handleRegister} class="space-y-4">
        <Input
          label="Company name"
          type="text"
          bind:value={companyName}
          icon={Building2}
          placeholder="Acme Corp"
          required
          disabled={submitting}
        />

        <Input
          label="Work email"
          type="email"
          bind:value={email}
          icon={Mail}
          placeholder="you@company.com"
          autocomplete="email"
          required
          disabled={submitting}
        />

        <Button type="submit" loading={submitting} disabled={submitting} class="w-full">
          {submitting ? 'Creating workspace...' : 'Create workspace'}
        </Button>
      </form>
    </Card>

    <p class="mt-6 text-center text-sm text-dark-text-muted">
      Already have an account?
      <a href="/auth/login" class="text-primary-400 hover:underline">Sign in</a>
    </p>
  </div>
</div>
