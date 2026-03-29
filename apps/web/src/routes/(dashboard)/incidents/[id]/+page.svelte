<script lang="ts">
  /**
   * T142: Incident detail/edit page — form with optimistic locking.
   */
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { apiClient, type Incident, type Category, type Severity, ApiError } from '$lib/api';
  import { isEditorOrAbove } from '$lib/stores/auth';
  import { Button, Card, Modal, PageHeader, LoadingSkeleton } from '$components/ui';

  const id = $derived($page.params.id);

  let incident = $state<Incident | null>(null);
  let loading = $state(true);
  let saving = $state(false);
  let deleting = $state(false);
  let error = $state<string | null>(null);
  let conflictError = $state<string | null>(null);
  let showDeleteConfirm = $state(false);
  let successMessage = $state<string | null>(null);

  // Form fields (bound to incident data)
  let title = $state('');
  let category = $state<Category>('unsafe-regex');
  let severity = $state<Severity>('medium');
  let antiPattern = $state('');
  let remediation = $state('');
  let codeExample = $state('');
  let sourceUrl = $state('');
  let organization = $state('');
  let affectedLanguages = $state('');
  let staticRulePossible = $state(false);

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

  async function load() {
    loading = true;
    error = null;
    try {
      incident = await apiClient.incidents.get(id!);
      populateForm(incident);
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Failed to load incident';
    } finally {
      loading = false;
    }
  }

  function populateForm(inc: Incident) {
    title = inc.title;
    category = inc.category;
    severity = inc.severity;
    antiPattern = inc.anti_pattern;
    remediation = inc.remediation;
    codeExample = inc.code_example ?? '';
    sourceUrl = inc.source_url ?? '';
    organization = inc.organization ?? '';
    affectedLanguages = inc.affected_languages.join(', ');
    staticRulePossible = inc.static_rule_possible;
  }

  async function handleSave(e: SubmitEvent) {
    e.preventDefault();
    if (!incident) return;

    saving = true;
    error = null;
    conflictError = null;
    successMessage = null;

    try {
      const updated = await apiClient.incidents.update(incident.id, {
        title,
        category,
        severity,
        anti_pattern: antiPattern,
        remediation,
        code_example: codeExample || undefined,
        source_url: sourceUrl || undefined,
        organization: organization || undefined,
        affected_languages: affectedLanguages
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        static_rule_possible: staticRulePossible,
        version: incident.version,
      });
      incident = updated;
      successMessage = 'Saved successfully';
    } catch (e) {
      if (e instanceof ApiError && e.code === 'CONFLICT') {
        conflictError = e.message;
      } else {
        error = e instanceof ApiError ? e.message : 'Save failed';
      }
    } finally {
      saving = false;
    }
  }

  async function handleReload() {
    conflictError = null;
    await load();
  }

  async function handleDelete() {
    if (!incident) return;
    deleting = true;
    error = null;

    try {
      await apiClient.incidents.delete(incident.id);
      await goto('/incidents');
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Delete failed';
      showDeleteConfirm = false;
    } finally {
      deleting = false;
    }
  }

  onMount(load);
</script>

<div class="mx-auto max-w-2xl">
  <!-- Back -->
  <a
    href="/incidents"
    class="mb-6 inline-flex items-center gap-1 text-sm text-light-text-muted hover:text-light-text"
  >
    ← Back to incidents
  </a>

  {#if loading}
    <div class="flex justify-center py-12">
      <LoadingSkeleton variant="text" lines={5} />
    </div>
  {:else if error && !incident}
    <div class="rounded-lg bg-error-light border border-error-border p-4 text-sm text-error-text">{error}</div>
  {:else if incident}
    <PageHeader title="Edit Incident">
      {#snippet actions()}
        {#if $isEditorOrAbove}
          <Button variant="danger" size="sm" onclick={() => (showDeleteConfirm = true)}>
            Delete
          </Button>
        {/if}
      {/snippet}
    </PageHeader>

    <!-- Conflict error -->
    {#if conflictError}
      <div class="mb-4 rounded-lg bg-status-pending-light border border-status-pending/30 p-4 text-sm text-status-pending-text">
        <strong>Conflict:</strong>
        {conflictError}
        <button onclick={handleReload} class="ml-2 underline">Reload</button>
      </div>
    {/if}

    <!-- General error -->
    {#if error}
      <div class="mb-4 rounded-lg bg-error-light border border-error-border p-3 text-sm text-error-text">{error}</div>
    {/if}

    <!-- Success -->
    {#if successMessage}
      <div class="mb-4 rounded-lg bg-status-active-light border border-status-active/30 p-3 text-sm text-status-active-text">{successMessage}</div>
    {/if}

    <Card>
      <form onsubmit={handleSave} class="space-y-5">
        <div>
          <label for="title" class="block text-sm font-medium text-light-text">Title *</label>
          <input
            id="title"
            type="text"
            bind:value={title}
            required
            disabled={!$isEditorOrAbove}
            class="mt-1 block w-full rounded-lg border border-light-border-strong bg-light-bg px-3 py-2 text-sm text-light-text focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none disabled:bg-neutral-50 disabled:opacity-50"
          />
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="category" class="block text-sm font-medium text-light-text">Category *</label>
            <select
              id="category"
              bind:value={category}
              disabled={!$isEditorOrAbove}
              class="mt-1 block w-full rounded-lg border border-light-border-strong bg-light-bg px-3 py-2 text-sm text-light-text focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none disabled:bg-neutral-50 disabled:opacity-50"
            >
              {#each categories as cat}
                <option value={cat}>{cat}</option>
              {/each}
            </select>
          </div>

          <div>
            <label for="severity" class="block text-sm font-medium text-light-text">Severity *</label>
            <select
              id="severity"
              bind:value={severity}
              disabled={!$isEditorOrAbove}
              class="mt-1 block w-full rounded-lg border border-light-border-strong bg-light-bg px-3 py-2 text-sm text-light-text focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none disabled:bg-neutral-50 disabled:opacity-50"
            >
              {#each severities as sev}
                <option value={sev}>{sev}</option>
              {/each}
            </select>
          </div>
        </div>

        <div>
          <label for="anti-pattern" class="block text-sm font-medium text-light-text"
            >Anti-pattern *</label
          >
          <textarea
            id="anti-pattern"
            bind:value={antiPattern}
            required
            rows={3}
            disabled={!$isEditorOrAbove}
            class="mt-1 block w-full rounded-lg border border-light-border-strong bg-light-bg px-3 py-2 text-sm text-light-text focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none disabled:bg-neutral-50 disabled:opacity-50"
          ></textarea>
        </div>

        <div>
          <label for="remediation" class="block text-sm font-medium text-light-text"
            >Remediation *</label
          >
          <textarea
            id="remediation"
            bind:value={remediation}
            required
            rows={3}
            disabled={!$isEditorOrAbove}
            class="mt-1 block w-full rounded-lg border border-light-border-strong bg-light-bg px-3 py-2 text-sm text-light-text focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none disabled:bg-neutral-50 disabled:opacity-50"
          ></textarea>
        </div>

        <div>
          <label for="code-example" class="block text-sm font-medium text-light-text"
            >Code example</label
          >
          <textarea
            id="code-example"
            bind:value={codeExample}
            rows={4}
            disabled={!$isEditorOrAbove}
            class="mt-1 block w-full rounded-lg border border-light-border-strong bg-light-bg px-3 py-2 font-mono text-xs text-light-text focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none disabled:bg-neutral-50 disabled:opacity-50"
          ></textarea>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="source-url" class="block text-sm font-medium text-light-text">Source URL</label>
            <input
              id="source-url"
              type="url"
              bind:value={sourceUrl}
              disabled={!$isEditorOrAbove}
              class="mt-1 block w-full rounded-lg border border-light-border-strong bg-light-bg px-3 py-2 text-sm text-light-text focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none disabled:bg-neutral-50 disabled:opacity-50"
            />
          </div>

          <div>
            <label for="organization" class="block text-sm font-medium text-light-text"
              >Organization</label
            >
            <input
              id="organization"
              type="text"
              bind:value={organization}
              disabled={!$isEditorOrAbove}
              class="mt-1 block w-full rounded-lg border border-light-border-strong bg-light-bg px-3 py-2 text-sm text-light-text focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none disabled:bg-neutral-50 disabled:opacity-50"
            />
          </div>
        </div>

        <div>
          <label for="languages" class="block text-sm font-medium text-light-text">
            Affected languages (comma-separated)
          </label>
          <input
            id="languages"
            type="text"
            bind:value={affectedLanguages}
            placeholder="python, javascript, go"
            disabled={!$isEditorOrAbove}
            class="mt-1 block w-full rounded-lg border border-light-border-strong bg-light-bg px-3 py-2 text-sm text-light-text focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 focus:outline-none disabled:bg-neutral-50 disabled:opacity-50"
          />
        </div>

        <div class="flex items-center gap-2">
          <input
            id="static-rule"
            type="checkbox"
            bind:checked={staticRulePossible}
            disabled={!$isEditorOrAbove}
            class="h-4 w-4 rounded border-light-border-strong text-primary-500"
          />
          <label for="static-rule" class="text-sm font-medium text-light-text">
            Static Semgrep rule possible
          </label>
        </div>

        <div class="flex items-center justify-between border-t border-light-border pt-4">
          <div class="text-xs text-light-text-muted">Version {incident.version}</div>

          {#if $isEditorOrAbove}
            <Button type="submit" loading={saving}>
              {saving ? 'Saving...' : 'Save'}
            </Button>
          {/if}
        </div>
      </form>
    </Card>
  {/if}
</div>

<!-- Delete confirmation modal -->
<Modal
  bind:open={showDeleteConfirm}
  onClose={() => (showDeleteConfirm = false)}
  title="Delete incident?"
>
  <p class="text-sm text-light-text-secondary">
    This will soft-delete the incident. If it has an active linked rule, deletion will be
    blocked.
  </p>

  {#if error}
    <div class="mt-3 rounded-lg bg-error-light border border-error-border p-3 text-sm text-error-text">{error}</div>
  {/if}

  {#snippet footer()}
    <div class="flex justify-end gap-3">
      <Button variant="secondary" onclick={() => (showDeleteConfirm = false)}>
        Cancel
      </Button>
      <Button variant="danger" loading={deleting} onclick={handleDelete}>
        {deleting ? 'Deleting...' : 'Confirm'}
      </Button>
    </div>
  {/snippet}
</Modal>
