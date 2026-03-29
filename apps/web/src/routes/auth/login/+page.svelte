<!--
  T018: Login page — Firebase Authentication (email/password + Google).
-->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { signInWithEmailAndPassword, signInWithPopup } from 'firebase/auth';
  import { auth, googleProvider } from '$lib/firebase';

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

<div class="flex min-h-screen items-center justify-center bg-gray-50">
  <div class="w-full max-w-sm rounded-xl bg-white p-8 shadow-sm ring-1 ring-gray-200">
    <div class="mb-8 text-center">
      <h1 class="text-2xl font-bold text-gray-900">Oute Muscle</h1>
      <p class="mt-1 text-sm text-gray-500">Sign in to your workspace</p>
    </div>

    {#if error}
      <div class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">
        {error}
      </div>
    {/if}

    <form onsubmit={handleEmailLogin} class="space-y-4">
      <div>
        <label for="email" class="block text-sm font-medium text-gray-700">Email</label>
        <input
          id="email"
          type="email"
          bind:value={email}
          required
          autocomplete="email"
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm
                 shadow-sm transition placeholder:text-gray-400
                 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
          placeholder="you@company.com"
        />
      </div>

      <div>
        <label for="password" class="block text-sm font-medium text-gray-700">Password</label>
        <input
          id="password"
          type="password"
          bind:value={password}
          required
          autocomplete="current-password"
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm
                 shadow-sm transition placeholder:text-gray-400
                 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
          placeholder="Your password"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        class="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5
               text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500
               disabled:cursor-not-allowed disabled:opacity-60"
      >
        {#if loading}
          <span class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
          ></span>
        {/if}
        Sign in
      </button>
    </form>

    <div class="relative my-6">
      <div class="absolute inset-0 flex items-center">
        <div class="w-full border-t border-gray-200"></div>
      </div>
      <div class="relative flex justify-center text-xs">
        <span class="bg-white px-2 text-gray-400">or</span>
      </div>
    </div>

    <button
      onclick={handleGoogleLogin}
      disabled={loading}
      class="flex w-full items-center justify-center gap-3 rounded-lg border border-gray-300
             px-4 py-2.5 text-sm font-medium text-gray-700 shadow-sm transition
             hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
    >
      <svg class="h-5 w-5" viewBox="0 0 24 24">
        <path
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
          fill="#4285F4"
        />
        <path
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          fill="#34A853"
        />
        <path
          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
          fill="#FBBC05"
        />
        <path
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
          fill="#EA4335"
        />
      </svg>
      Sign in with Google
    </button>

    <p class="mt-6 text-center text-xs text-gray-400">
      By continuing you agree to our
      <a href="https://muscle.oute.pro/terms" class="underline">Terms of Service</a>.
    </p>
  </div>
</div>
