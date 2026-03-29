<!--
  T019: Pending approval page.
  Shown to users who have no tenant assigned yet.
-->
<script lang="ts">
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

<div class="flex min-h-screen items-center justify-center bg-gray-50">
  <div class="w-full max-w-md rounded-xl bg-white p-8 text-center shadow-sm ring-1 ring-gray-200">
    <div class="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-amber-100">
      <svg
        class="h-8 w-8 text-amber-600"
        fill="none"
        viewBox="0 0 24 24"
        stroke-width="1.5"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
        />
      </svg>
    </div>

    <h1 class="text-xl font-semibold text-gray-900">Pending Approval</h1>
    <p class="mt-3 text-sm leading-relaxed text-gray-500">
      Your account is pending approval. An administrator will assign you to a team.
    </p>

    <button
      onclick={handleLogout}
      disabled={loggingOut}
      class="mt-8 inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2
             text-sm font-medium text-gray-700 transition hover:bg-gray-50
             disabled:cursor-not-allowed disabled:opacity-60"
    >
      {#if loggingOut}
        <span
          class="h-4 w-4 animate-spin rounded-full border-2 border-gray-400 border-t-transparent"
        ></span>
        Logging out...
      {:else}
        Sign out
      {/if}
    </button>
  </div>
</div>
