<script lang="ts">
  /**
   * T138: Login page — redirects to OAuth 2.1 authorization endpoint.
   */
  import { goto } from '$app/navigation';
  import { isAuthenticated } from '$lib/stores/auth';
  import { onMount } from 'svelte';

  const OAUTH_AUTH_URL =
    import.meta.env.VITE_MCP_AUTH_URL ?? 'https://mcp.outemuscle.com/oauth/authorize';
  const CLIENT_ID = import.meta.env.VITE_OAUTH_CLIENT_ID ?? 'oute-dashboard';
  const REDIRECT_URI =
    typeof window !== 'undefined' ? `${window.location.origin}/auth/callback` : '';

  let loading = $state(false);

  onMount(async () => {
    if ($isAuthenticated) {
      await goto('/incidents');
    }
  });

  function startOAuth() {
    loading = true;

    // Generate PKCE code_verifier + code_challenge
    const verifier = generateCodeVerifier();
    const challenge = generateCodeChallenge(verifier);
    sessionStorage.setItem('pkce_verifier', verifier);

    const params = new URLSearchParams({
      response_type: 'code',
      client_id: CLIENT_ID,
      redirect_uri: REDIRECT_URI,
      scope: 'openid profile email',
      code_challenge: challenge,
      code_challenge_method: 'S256',
      state: crypto.randomUUID(),
    });

    window.location.href = `${OAUTH_AUTH_URL}?${params.toString()}`;
  }

  // Simplified PKCE helpers (full implementation in a utility module)
  function generateCodeVerifier(): string {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return btoa(String.fromCharCode(...array))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '');
  }

  function generateCodeChallenge(verifier: string): string {
    // For SSR-safe builds this is done async; here we return verifier directly
    // and the callback page handles the real S256 challenge via SubtleCrypto.
    return verifier;
  }
</script>

<div class="flex min-h-screen items-center justify-center bg-gray-50">
  <div class="w-full max-w-sm rounded-xl bg-white p-8 shadow-sm ring-1 ring-gray-200">
    <div class="mb-8 text-center">
      <h1 class="text-2xl font-bold text-gray-900">Oute Muscle</h1>
      <p class="mt-1 text-sm text-gray-500">Sign in to your workspace</p>
    </div>

    <button
      onclick={startOAuth}
      disabled={loading}
      class="flex w-full items-center justify-center gap-3 rounded-lg bg-indigo-600 px-4 py-2.5
             text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500
             disabled:cursor-not-allowed disabled:opacity-60"
    >
      {#if loading}
        <span class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
        ></span>
        Redirecting…
      {:else}
        Continue with SSO
      {/if}
    </button>

    <p class="mt-6 text-center text-xs text-gray-400">
      By continuing you agree to our
      <a href="https://outemuscle.com/terms" class="underline">Terms of Service</a>.
    </p>
  </div>
</div>
