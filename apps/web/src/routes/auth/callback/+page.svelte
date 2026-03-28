<script lang="ts">
  /**
   * T138: OAuth 2.1 callback page — exchanges code for token, stores in auth store.
   */
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth';

  const TOKEN_URL = import.meta.env.VITE_MCP_TOKEN_URL ?? 'https://mcp.outemuscle.com/oauth/token';
  const CLIENT_ID = import.meta.env.VITE_OAUTH_CLIENT_ID ?? 'oute-dashboard';

  let error = $state<string | null>(null);
  let status = $state('Completing sign-in…');

  onMount(async () => {
    try {
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      // state parameter reserved for CSRF validation in future
      const _returnedState = params.get('state');

      if (!code) throw new Error('Missing authorization code');

      const verifier = sessionStorage.getItem('pkce_verifier');
      if (!verifier) throw new Error('Missing PKCE verifier — please start the login flow again');

      sessionStorage.removeItem('pkce_verifier');

      status = 'Exchanging code for token…';

      const response = await fetch(TOKEN_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          grant_type: 'authorization_code',
          code,
          redirect_uri: `${window.location.origin}/auth/callback`,
          client_id: CLIENT_ID,
          code_verifier: verifier,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error_description ?? `Token exchange failed (${response.status})`);
      }

      const { access_token, id_token } = await response.json();
      const token = access_token ?? id_token;

      // Decode JWT payload (base64url) to get user info
      const [, payloadB64] = token.split('.');
      const payload = JSON.parse(atob(payloadB64.replace(/-/g, '+').replace(/_/g, '/')));

      auth.login(token, {
        id: payload.sub,
        email: payload.email,
        role: payload['https://outemuscle.com/role'] ?? 'viewer',
      });

      await goto('/incidents');
    } catch (e) {
      error = e instanceof Error ? e.message : 'Unknown error during sign-in';
    }
  });
</script>

<div class="flex min-h-screen items-center justify-center bg-gray-50">
  <div class="w-full max-w-sm rounded-xl bg-white p-8 text-center shadow-sm ring-1 ring-gray-200">
    {#if error}
      <div class="mb-4 rounded-lg bg-red-50 p-4 text-left text-sm text-red-700">{error}</div>
      <a href="/auth/login" class="text-sm text-indigo-600 hover:underline">Back to login</a>
    {:else}
      <div class="mb-4 flex justify-center">
        <span
          class="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent"
        ></span>
      </div>
      <p class="text-sm text-gray-600">{status}</p>
    {/if}
  </div>
</div>
