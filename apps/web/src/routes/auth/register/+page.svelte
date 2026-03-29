<script lang="ts">
  /**
   * T138: Register page — workspace registration (new tenant sign-up).
   * Collects company name + user email, then starts OAuth flow.
   */
  import { goto } from '$app/navigation';

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

<div class="flex min-h-screen items-center justify-center bg-gray-50">
  <div class="w-full max-w-sm rounded-xl bg-white p-8 shadow-sm ring-1 ring-gray-200">
    <div class="mb-8 text-center">
      <h1 class="text-2xl font-bold text-gray-900">Create workspace</h1>
      <p class="mt-1 text-sm text-gray-500">Get started with Oute Muscle</p>
    </div>

    {#if error}
      <div class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
    {/if}

    <form onsubmit={handleRegister} class="space-y-4">
      <div>
        <label for="company" class="block text-sm font-medium text-gray-700">Company name</label>
        <input
          id="company"
          type="text"
          bind:value={companyName}
          required
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm
                 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
          placeholder="Acme Corp"
        />
      </div>

      <div>
        <label for="email" class="block text-sm font-medium text-gray-700">Work email</label>
        <input
          id="email"
          type="email"
          bind:value={email}
          required
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm
                 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
          placeholder="you@company.com"
        />
      </div>

      <button
        type="submit"
        disabled={submitting}
        class="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm
               transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {submitting ? 'Creating workspace…' : 'Create workspace'}
      </button>
    </form>

    <p class="mt-4 text-center text-sm text-gray-500">
      Already have an account?
      <a href="/auth/login" class="text-indigo-600 hover:underline">Sign in</a>
    </p>
  </div>
</div>
