<!--
  T018: Login page — Firebase Authentication (email/password + Google).
-->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { signInWithEmailAndPassword, signInWithPopup } from 'firebase/auth';
  import { auth, googleProvider } from '$lib/firebase';
  import { Button, Input, Card } from '$components/ui';
  import { Mail, Lock } from 'lucide-svelte';

  let email = $state('');
  let password = $state('');
  let error = $state<string | null>(null);
  let loading = $state(false);

  async function exchangeSession(idToken: string): Promise<void> {
    const res = await fetch('/api/auth/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ idToken }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error ?? `Session exchange failed (${res.status})`);
    }
  }

  async function handleEmailLogin(e: Event) {
    e.preventDefault();
    error = null;
    loading = true;

    try {
      const credential = await signInWithEmailAndPassword(auth, email, password);
      const idToken = await credential.user.getIdToken();
      await exchangeSession(idToken);
      await goto('/');
    } catch (err) {
      if (err instanceof Error) {
        // Map Firebase error codes to user-friendly messages
        if (err.message.includes('auth/invalid-credential')) {
          error = 'Invalid email or password.';
        } else if (err.message.includes('auth/user-not-found')) {
          error = 'No account found with this email.';
        } else if (err.message.includes('auth/wrong-password')) {
          error = 'Incorrect password.';
        } else if (err.message.includes('auth/too-many-requests')) {
          error = 'Too many failed attempts. Please try again later.';
        } else {
          error = err.message;
        }
      } else {
        error = 'An unexpected error occurred.';
      }
    } finally {
      loading = false;
    }
  }

  async function handleGoogleLogin() {
    error = null;
    loading = true;

    try {
      const credential = await signInWithPopup(auth, googleProvider);
      const idToken = await credential.user.getIdToken();
      await exchangeSession(idToken);
      await goto('/');
    } catch (err) {
      if (err instanceof Error) {
        if (err.message.includes('auth/popup-closed-by-user')) {
          error = null; // User cancelled — not an error
        } else {
          error = err.message;
        }
      } else {
        error = 'An unexpected error occurred.';
      }
    } finally {
      loading = false;
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
      <p class="text-sm text-dark-text-muted">Sign in to your workspace</p>
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

      <form onsubmit={handleEmailLogin} class="space-y-4">
        <Input
          label="Email"
          type="email"
          bind:value={email}
          icon={Mail}
          placeholder="you@company.com"
          autocomplete="email"
          required
          disabled={loading}
        />

        <Input
          label="Password"
          type="password"
          bind:value={password}
          icon={Lock}
          placeholder="Your password"
          autocomplete="current-password"
          required
          disabled={loading}
        />

        <Button type="submit" {loading} disabled={loading} class="w-full">
          Sign in
        </Button>
      </form>

      <div class="relative my-6">
        <div class="absolute inset-0 flex items-center">
          <div class="w-full border-t border-light-border"></div>
        </div>
        <div class="relative flex justify-center text-xs">
          <span class="bg-light-bg px-2 text-light-text-muted">or</span>
        </div>
      </div>

      <button
        onclick={handleGoogleLogin}
        disabled={loading}
        class="flex w-full items-center justify-center gap-3 rounded-lg border border-light-border-strong
               bg-light-bg px-4 py-2.5 text-sm font-medium text-light-text shadow-sm transition
               hover:bg-light-bg-hover disabled:cursor-not-allowed disabled:opacity-60"
      >
        <svg class="h-5 w-5" viewBox="0 0 24 24">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
        </svg>
        Continue with Google
      </button>
    </Card>

    <p class="mt-6 text-center text-xs text-dark-text-dimmed">
      By continuing you agree to our
      <a href="https://muscle.oute.pro/terms" class="text-primary-400 hover:underline">Terms of Service</a>.
    </p>
  </div>
</div>
