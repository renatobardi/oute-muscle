<script lang="ts">
  /**
   * T143: Ingest incident from URL — paste URL → review LLM draft → confirm.
   */
  import { goto } from '$app/navigation';
  import { apiClient, type IncidentDraft, type Category, type Severity, ApiError } from '$lib/api';
  import { Button, Card, PageHeader } from '$components/ui';

  let url = $state('');
  let extracting = $state(false);
  let confirming = $state(false);
  let draft = $state<IncidentDraft | null>(null);
  let error = $state<string | null>(null);

  const categories: Category[] = [
    'unsafe-regex',
    'race-condition',
    'missing-error-handling',
    'injection',
    'resource-exhaustion',
    'missing-safety-check',
    'deployment-error',
    'data-consistency',
    'unsafe-api-usage',
    'cascading-failure',
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
  <a
    href="/incidents"
    class="mb-6 inline-flex items-center gap-1 text-sm text-light-text-muted hover:text-light-text"
  >
    ← Back to incidents
  </a>

  <PageHeader title="Ingest from URL" />

  <!-- Step 1: URL input -->
  <form onsubmit={handleExtract} class="mb-6 flex gap-3">
    <input
      id="url"
      type="url"
      aria-label="URL"
      placeholder="https://blog.example.com/post-mortem"
      bind:value={url}
      required
      class="flex-1 rounded-lg border border-light-border-strong bg-light-bg px-3 py-2 text-sm text-light-text placeholder:text-light-text-muted focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none"
    />
    <Button type="submit" loading={extracting}>
      {extracting ? 'Extracting...' : 'Extract'}
    </Button>
  </form>

  {#if error}
    <div class="mb-4 rounded-lg bg-error-light border border-error-border p-3 text-sm text-error-text">{error}</div>
  {/if}

  <!-- Step 2: Review draft -->
  {#if draft}
    <Card class="border-primary-200 bg-primary-50/30">
      <p class="mb-4 text-xs font-semibold tracking-wider text-primary-500 uppercase">
        Review extracted draft
      </p>

      <div class="space-y-4">
        <div>
          <label for="draft-title" class="block text-sm font-medium text-light-text">Title</label>
          <input
            id="draft-title"
            type="text"
            bind:value={draft.title}
            class="mt-1 block w-full rounded-lg border border-light-border-strong bg-light-bg px-3 py-2 text-sm text-light-text focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none"
          />
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="draft-category" class="block text-sm font-medium text-light-text"
              >Category</label
            >
            <select
              id="draft-category"
              bind:value={draft.category}
              class="mt-1 block w-full rounded-lg border border-light-border-strong bg-light-bg px-3 py-2 text-sm text-light-text focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none"
            >
              {#each categories as cat}
                <option value={cat}>{cat}</option>
              {/each}
            </select>
          </div>
          <div>
            <label for="draft-severity" class="block text-sm font-medium text-light-text"
              >Severity</label
            >
            <select
              id="draft-severity"
              bind:value={draft.severity}
              class="mt-1 block w-full rounded-lg border border-light-border-strong bg-light-bg px-3 py-2 text-sm text-light-text focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none"
            >
              {#each severities as sev}
                <option value={sev}>{sev}</option>
              {/each}
            </select>
          </div>
        </div>

        <div>
          <label for="draft-anti" class="block text-sm font-medium text-light-text"
            >Anti-pattern</label
          >
          <textarea
            id="draft-anti"
            bind:value={draft.anti_pattern}
            rows={3}
            class="mt-1 block w-full rounded-lg border border-light-border-strong bg-light-bg px-3 py-2 text-sm text-light-text focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none"
          ></textarea>
        </div>

        <div>
          <label for="draft-remediation" class="block text-sm font-medium text-light-text"
            >Remediation</label
          >
          <textarea
            id="draft-remediation"
            bind:value={draft.remediation}
            rows={3}
            class="mt-1 block w-full rounded-lg border border-light-border-strong bg-light-bg px-3 py-2 text-sm text-light-text focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none"
          ></textarea>
        </div>

        {#if draft.organization}
          <p class="text-xs text-light-text-muted">
            Organization (LLM-extracted): <strong>{draft.organization}</strong>
          </p>
        {/if}
      </div>

      <div class="mt-5 flex justify-end gap-3">
        <Button variant="secondary" onclick={() => (draft = null)}>
          Discard
        </Button>
        <Button loading={confirming} onclick={handleConfirm}>
          {confirming ? 'Saving...' : 'Confirm'}
        </Button>
      </div>
    </Card>
  {/if}
</div>
