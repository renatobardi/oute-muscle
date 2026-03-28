<script lang="ts">
  /**
   * T142: Incident detail/edit page — form with optimistic locking.
   */
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { apiClient, type Incident, type Category, type Severity, ApiError } from '$lib/api';
  import { isEditorOrAbove } from '$lib/stores/auth';

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
      incident = await apiClient.incidents.get(id);
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
    class="mb-6 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900"
  >
    ← Back to incidents
  </a>

  {#if loading}
    <div class="flex justify-center py-12">
      <span
        class="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent"
      ></span>
    </div>
  {:else if error && !incident}
    <div class="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
  {:else if incident}
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-bold text-gray-900">Edit Incident</h1>
      {#if $isEditorOrAbove}
        <button
          onclick={() => (showDeleteConfirm = true)}
          class="rounded-lg border border-red-300 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50"
          >Delete</button
        >
      {/if}
    </div>

    <!-- Conflict error -->
    {#if conflictError}
      <div class="mb-4 rounded-lg bg-yellow-50 p-4 text-sm text-yellow-800">
        <strong>Conflict:</strong>
        {conflictError}
        <button onclick={handleReload} class="ml-2 underline">Reload</button>
      </div>
    {/if}

    <!-- General error -->
    {#if error}
      <div class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
    {/if}

    <!-- Success -->
    {#if successMessage}
      <div class="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">{successMessage}</div>
    {/if}

    <form onsubmit={handleSave} class="space-y-5">
      <div>
        <label for="title" class="block text-sm font-medium text-gray-700">Title *</label>
        <input
          id="title"
          type="text"
          bind:value={title}
          required
          disabled={!$isEditorOrAbove}
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none disabled:bg-gray-50"
        />
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label for="category" class="block text-sm font-medium text-gray-700">Category *</label>
          <select
            id="category"
            bind:value={category}
            disabled={!$isEditorOrAbove}
            class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none disabled:bg-gray-50"
          >
            {#each categories as cat}
              <option value={cat}>{cat}</option>
            {/each}
          </select>
        </div>

        <div>
          <label for="severity" class="block text-sm font-medium text-gray-700">Severity *</label>
          <select
            id="severity"
            bind:value={severity}
            disabled={!$isEditorOrAbove}
            class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none disabled:bg-gray-50"
          >
            {#each severities as sev}
              <option value={sev}>{sev}</option>
            {/each}
          </select>
        </div>
      </div>

      <div>
        <label for="anti-pattern" class="block text-sm font-medium text-gray-700"
          >Anti-pattern *</label
        >
        <textarea
          id="anti-pattern"
          bind:value={antiPattern}
          required
          rows={3}
          disabled={!$isEditorOrAbove}
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none disabled:bg-gray-50"
        ></textarea>
      </div>

      <div>
        <label for="remediation" class="block text-sm font-medium text-gray-700"
          >Remediation *</label
        >
        <textarea
          id="remediation"
          bind:value={remediation}
          required
          rows={3}
          disabled={!$isEditorOrAbove}
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none disabled:bg-gray-50"
        ></textarea>
      </div>

      <div>
        <label for="code-example" class="block text-sm font-medium text-gray-700"
          >Code example</label
        >
        <textarea
          id="code-example"
          bind:value={codeExample}
          rows={4}
          disabled={!$isEditorOrAbove}
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none disabled:bg-gray-50"
        ></textarea>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label for="source-url" class="block text-sm font-medium text-gray-700">Source URL</label>
          <input
            id="source-url"
            type="url"
            bind:value={sourceUrl}
            disabled={!$isEditorOrAbove}
            class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none disabled:bg-gray-50"
          />
        </div>

        <div>
          <label for="organization" class="block text-sm font-medium text-gray-700"
            >Organization</label
          >
          <input
            id="organization"
            type="text"
            bind:value={organization}
            disabled={!$isEditorOrAbove}
            class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none disabled:bg-gray-50"
          />
        </div>
      </div>

      <div>
        <label for="languages" class="block text-sm font-medium text-gray-700">
          Affected languages (comma-separated)
        </label>
        <input
          id="languages"
          type="text"
          bind:value={affectedLanguages}
          placeholder="python, javascript, go"
          disabled={!$isEditorOrAbove}
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none disabled:bg-gray-50"
        />
      </div>

      <div class="flex items-center gap-2">
        <input
          id="static-rule"
          type="checkbox"
          bind:checked={staticRulePossible}
          disabled={!$isEditorOrAbove}
          class="h-4 w-4 rounded border-gray-300 text-indigo-600"
        />
        <label for="static-rule" class="text-sm font-medium text-gray-700">
          Static Semgrep rule possible
        </label>
      </div>

      <div class="flex items-center justify-between border-t border-gray-100 pt-4">
        <div class="text-xs text-gray-400">Version {incident.version}</div>

        {#if $isEditorOrAbove}
          <button
            type="submit"
            disabled={saving}
            class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        {/if}
      </div>
    </form>
  {/if}
</div>

<!-- Delete confirmation modal -->
{#if showDeleteConfirm}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
    <div class="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
      <h2 class="text-lg font-semibold text-gray-900">Delete incident?</h2>
      <p class="mt-2 text-sm text-gray-500">
        This will soft-delete the incident. If it has an active linked rule, deletion will be
        blocked.
      </p>

      {#if error}
        <div class="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
      {/if}

      <div class="mt-5 flex justify-end gap-3">
        <button
          onclick={() => (showDeleteConfirm = false)}
          class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >Cancel</button
        >
        <button
          onclick={handleDelete}
          disabled={deleting}
          class="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-60"
        >
          {deleting ? 'Deleting…' : 'Confirm'}
        </button>
      </div>
    </div>
  </div>
{/if}
