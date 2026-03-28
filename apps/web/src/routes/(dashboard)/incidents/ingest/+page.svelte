<script lang="ts">
  /**
   * T143: Ingest incident from URL — paste URL → review LLM draft → confirm.
   */
  import { goto } from '$app/navigation';
  import { apiClient, type IncidentDraft, type Category, type Severity, ApiError } from '$lib/api';

  let url = $state('');
  let extracting = $state(false);
  let confirming = $state(false);
  let draft = $state<IncidentDraft | null>(null);
  let error = $state<string | null>(null);

  const categories: Category[] = [
    'unsafe-regex', 'race-condition', 'missing-error-handling', 'injection',
    'resource-exhaustion', 'missing-safety-check', 'deployment-error',
    'data-consistency', 'unsafe-api-usage', 'cascading-failure',
  ];

  const severities: Severity[] = ['critical', 'high', 'medium', 'low'];

  async function handleExtract(e: SubmitEvent) {
    e.preventDefault();
    extracting = true;
    error = null;
    draft = null;

    try {
      const result = await apiClient.incidents.ingestUrl(url);
      draft = result.draft;
    } catch (e_) {
      if (e_ instanceof ApiError && e_.code === 'CONFLICT') {
        error = 'This URL has already been ingested.';
      } else {
        error = e_ instanceof ApiError ? e_.message : 'Extraction failed';
      }
    } finally {
      extracting = false;
    }
  }

  async function handleConfirm() {
    if (!draft) return;
    confirming = true;
    error = null;

    try {
      const incident = await apiClient.incidents.create(draft);
      await goto(`/incidents/${incident.id}`);
    } catch (e_) {
      error = e_ instanceof ApiError ? e_.message : 'Failed to save incident';
      confirming = false;
    }
  }
</script>

<div class="mx-auto max-w-2xl">
  <a href="/incidents" class="mb-6 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900">
    ← Back to incidents
  </a>

  <h1 class="mb-6 text-2xl font-bold text-gray-900">Ingest from URL</h1>

  <!-- Step 1: URL input -->
  <form onsubmit={handleExtract} class="mb-6 flex gap-3">
    <input
      id="url"
      type="url"
      aria-label="URL"
      placeholder="https://blog.example.com/post-mortem"
      bind:value={url}
      required
      class="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
    />
    <button
      type="submit"
      disabled={extracting}
      class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
    >
      {extracting ? 'Extracting…' : 'Extract'}
    </button>
  </form>

  {#if error}
    <div class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
  {/if}

  <!-- Step 2: Review draft -->
  {#if draft}
    <div class="rounded-xl border border-indigo-200 bg-indigo-50 p-1">
      <div class="rounded-lg bg-white p-5">
        <p class="mb-4 text-xs font-semibold uppercase tracking-wider text-indigo-600">
          Review extracted draft
        </p>

        <div class="space-y-4">
          <div>
            <label for="draft-title" class="block text-sm font-medium text-gray-700">Title</label>
            <input
              id="draft-title"
              type="text"
              bind:value={draft.title}
              class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="draft-category" class="block text-sm font-medium text-gray-700">Category</label>
              <select
                id="draft-category"
                bind:value={draft.category}
                class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                {#each categories as cat}
                  <option value={cat}>{cat}</option>
                {/each}
              </select>
            </div>
            <div>
              <label for="draft-severity" class="block text-sm font-medium text-gray-700">Severity</label>
              <select
                id="draft-severity"
                bind:value={draft.severity}
                class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                {#each severities as sev}
                  <option value={sev}>{sev}</option>
                {/each}
              </select>
            </div>
          </div>

          <div>
            <label for="draft-anti" class="block text-sm font-medium text-gray-700">Anti-pattern</label>
            <textarea
              id="draft-anti"
              bind:value={draft.anti_pattern}
              rows={3}
              class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            ></textarea>
          </div>

          <div>
            <label for="draft-remediation" class="block text-sm font-medium text-gray-700">Remediation</label>
            <textarea
              id="draft-remediation"
              bind:value={draft.remediation}
              rows={3}
              class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            ></textarea>
          </div>

          {#if draft.organization}
            <p class="text-xs text-gray-500">
              Organization (LLM-extracted): <strong>{draft.organization}</strong>
            </p>
          {/if}
        </div>

        <div class="mt-5 flex justify-end gap-3">
          <button
            onclick={() => (draft = null)}
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >Discard</button>
          <button
            onclick={handleConfirm}
            disabled={confirming}
            class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
          >
            {confirming ? 'Saving…' : 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>
