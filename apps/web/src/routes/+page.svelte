<script lang="ts">
  /**
   * Landing page — muscle.oute.pro
   * Dark, developer-focused, Vercel/Linear aesthetic.
   * Captures beta waitlist emails via POST /v1/waitlist.
   */
  import { Shield, Brain, Sparkles, FileText, Clock, Flame } from 'lucide-svelte';
  let email = $state('');
  let name = $state('');
  let company = $state('');
  let status: 'idle' | 'loading' | 'success' | 'error' = $state('idle');
  let errorMsg = $state('');
  let emailError = $state('');
  let step: 1 | 2 = $state(1);

  // API URL — override via PUBLIC_API_URL env var at build time if needed
  const API_BASE = 'https://muscle.oute.pro/api';

  function validateEmail(): boolean {
    if (!email) {
      emailError = 'Please enter your email address.';
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      emailError = 'Please enter a valid email address.';
      return false;
    }
    emailError = '';
    return true;
  }

  async function submitToAPI() {
    status = 'loading';
    errorMsg = '';

    try {
      const res = await fetch(`${API_BASE}/v1/waitlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, name: name || undefined, company: company || undefined }),
      });

      if (res.ok || res.status === 200) {
        status = 'success';
      } else {
        const body = await res.json().catch(() => ({}));
        errorMsg = body?.error ?? 'Something went wrong. Please try again.';
        status = 'error';
      }
    } catch {
      errorMsg = 'Network error. Please check your connection.';
      status = 'error';
    }
  }

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    if (step === 1) {
      if (!validateEmail()) return;
      step = 2;
    } else {
      await submitToAPI();
    }
  }

  async function handleSkip() {
    await submitToAPI();
  }
</script>

<svelte:head>
  <title>Oute Muscle — Stop repeating production incidents</title>
  <meta
    name="description"
    content="Oute Muscle turns your post-mortems into code guardrails. Every incident becomes a rule that blocks the same mistake from ever reaching production again."
  />
</svelte:head>

<!-- ─────────────────────────────────────────────────────── NAV -->
<nav class="fixed top-0 z-50 w-full border-b border-white/5 bg-black/80 backdrop-blur-md">
  <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
    <span class="font-mono text-sm font-semibold tracking-tight text-white">
      oute<span class="text-violet-400">.</span>muscle
    </span>
    <a
      href="#waitlist"
      class="rounded-lg bg-violet-600 px-4 py-1.5 text-sm font-semibold text-white transition hover:bg-violet-500"
    >
      Join waitlist
    </a>
  </div>
</nav>

<!-- ─────────────────────────────────────────────────────── HERO -->
<main class="min-h-screen bg-[#080808] text-white">
  <section class="relative overflow-hidden pt-40 pb-32">
    <!-- subtle grid background -->
    <div
      class="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,#ffffff08_1px,transparent_1px),linear-gradient(to_bottom,#ffffff08_1px,transparent_1px)] bg-[size:48px_48px]"
    ></div>
    <!-- glow -->
    <div
      class="pointer-events-none absolute top-0 left-1/2 h-[500px] w-[700px] -translate-x-1/2 rounded-full bg-violet-600/10 blur-[120px]"
    ></div>

    <div class="relative mx-auto max-w-4xl px-6 text-center">
      <div
        class="mb-6 inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-4 py-1.5 text-xs font-medium text-violet-300"
      >
        <span class="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-violet-400"></span>
        Private beta — limited access
      </div>

      <h1 class="text-5xl font-bold tracking-tight text-white sm:text-6xl lg:text-7xl">
        Stop repeating<br />
        <span class="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
          production incidents
        </span>
      </h1>

      <p class="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-white/70">
        Oute Muscle turns your post-mortems into code guardrails. Every incident becomes a detection
        rule that blocks the same mistake from ever reaching production again.
      </p>

      <!-- CTA form -->
      <div id="waitlist" class="mx-auto mt-12 max-w-md scroll-mt-24">
        {#if status === 'success'}
          <div class="rounded-xl border border-green-500/30 bg-green-500/10 px-6 py-8 text-center">
            <p class="text-2xl">🎉</p>
            <p class="mt-2 font-semibold text-green-400">You're on the list!</p>
            <p class="mt-1 text-sm text-white/60">We'll reach out as soon as a spot opens up.</p>
          </div>
        {:else if step === 1}
          <form onsubmit={handleSubmit} class="space-y-3">
            <div class="flex gap-2">
              <input
                type="email"
                bind:value={email}
                onblur={() => {
                  if (email) validateEmail();
                }}
                required
                placeholder="you@company.com"
                aria-label="Email address"
                aria-describedby={emailError ? 'email-error' : undefined}
                aria-invalid={emailError ? 'true' : undefined}
                class="flex-1 rounded-lg border bg-white/5 px-4 py-3 text-sm text-white placeholder:text-white/40 focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/30 focus:outline-none {emailError
                  ? 'border-red-500/60'
                  : 'border-white/10'}"
              />
              <button
                type="submit"
                class="shrink-0 rounded-lg bg-violet-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-violet-500"
              >
                Join waitlist
              </button>
            </div>

            {#if emailError}
              <p id="email-error" class="text-sm text-red-400">{emailError}</p>
            {/if}

            {#if status === 'error'}
              <p class="text-sm text-red-400">{errorMsg}</p>
            {/if}
          </form>
          <p class="mt-3 text-xs text-white/50">No spam. Invite-only beta. Unsubscribe anytime.</p>
        {:else}
          <form onsubmit={handleSubmit} class="space-y-3">
            <p class="text-sm text-white/60">
              Almost there! Tell us a bit more <span class="text-white/40">(optional)</span>
            </p>
            <input
              type="text"
              bind:value={name}
              placeholder="Your name"
              aria-label="Your name"
              class="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-white/40 focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/30 focus:outline-none"
            />
            <input
              type="text"
              bind:value={company}
              placeholder="Company"
              aria-label="Company"
              class="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-white/40 focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/30 focus:outline-none"
            />

            {#if status === 'error'}
              <p class="text-sm text-red-400">{errorMsg}</p>
            {/if}

            <button
              type="submit"
              disabled={status === 'loading'}
              class="w-full rounded-lg bg-violet-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
            >
              {status === 'loading' ? 'Sending...' : 'Complete sign-up'}
            </button>
            <button
              type="button"
              onclick={handleSkip}
              disabled={status === 'loading'}
              class="w-full text-sm text-white/50 transition hover:text-white/70 disabled:opacity-50"
            >
              Skip — just add me to the list
            </button>
          </form>
        {/if}
      </div>
    </div>
  </section>

  <!-- ─────────────────────────────────────────────────────── PROBLEM -->
  <section class="border-t border-white/5 py-24">
    <div class="mx-auto max-w-5xl px-6">
      <p class="text-center font-mono text-xs tracking-widest text-white/40 uppercase">
        The problem
      </p>
      <h2 class="mt-4 text-center text-3xl font-bold text-white sm:text-4xl">
        Every team has a graveyard of avoidable incidents
      </h2>
      <p class="mx-auto mt-4 max-w-2xl text-center text-white/70">
        You write the post-mortem, add an action item, and move on. Three sprints later, a new
        engineer makes the same mistake. The incident repeats. The post-mortem is forgotten.
      </p>

      <div class="mt-16 grid gap-6 sm:grid-cols-3">
        <div class="rounded-xl border border-white/10 bg-white/5 p-6">
          <FileText class="h-8 w-8 text-white/60" />
          <p class="mt-3 font-semibold text-white">Post-mortem written</p>
          <p class="mt-1 text-sm text-white/60">
            Root cause documented. Action items created. Filed away and forgotten.
          </p>
        </div>
        <div class="rounded-xl border border-white/10 bg-white/5 p-6">
          <Clock class="h-8 w-8 text-white/60" />
          <p class="mt-3 font-semibold text-white">3 sprints later</p>
          <p class="mt-1 text-sm text-white/60">
            New engineer joins. Same pattern coded. Same regex. Same race condition.
          </p>
        </div>
        <div class="rounded-xl border border-white/10 bg-white/5 p-6">
          <Flame class="h-8 w-8 text-white/60" />
          <p class="mt-3 font-semibold text-white">Incident repeats</p>
          <p class="mt-1 text-sm text-white/60">
            Same alert fires. Same on-call woken. Same post-mortem written.
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- ─────────────────────────────────────────────────────── HOW IT WORKS -->
  <section class="border-t border-white/5 py-24">
    <div class="mx-auto max-w-5xl px-6">
      <p class="text-center font-mono text-xs tracking-widest text-white/40 uppercase">
        How it works
      </p>
      <h2 class="mt-4 text-center text-3xl font-bold text-white sm:text-4xl">
        Three layers. One goal: incidents that never repeat.
      </h2>

      <div class="mt-16">
        <!-- L1 — Static Guardrails -->
        <div class="flex gap-5">
          <div class="flex shrink-0 flex-col items-center">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-red-500/15">
              <Shield class="h-5 w-5 text-red-400" />
            </div>
            <div class="w-px flex-1 bg-gradient-to-b from-red-500/40 to-amber-500/40"></div>
          </div>
          <div class="flex-1 pb-8">
            <div class="flex flex-wrap items-center gap-2">
              <span class="font-mono text-xs font-bold text-red-400">L1</span>
              <span
                class="rounded-full bg-red-500/20 px-2 py-0.5 font-mono text-xs font-medium text-red-400"
                >BLOCKING</span
              >
            </div>
            <h3 class="mt-1 font-semibold text-white">Semgrep rules synthesized from incidents</h3>
            <p class="mt-1 text-sm text-white/60">
              Every post-mortem automatically becomes a Semgrep rule. The pattern that caused the
              incident is blocked at CI time — before the PR even lands.
            </p>
          </div>
        </div>

        <!-- L2 — RAG Advisory -->
        <div class="flex gap-5">
          <div class="flex shrink-0 flex-col items-center">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/15">
              <Brain class="h-5 w-5 text-amber-400" />
            </div>
            <div class="w-px flex-1 bg-gradient-to-b from-amber-500/40 to-violet-500/40"></div>
          </div>
          <div class="flex-1 pb-8">
            <div class="flex flex-wrap items-center gap-2">
              <span class="font-mono text-xs font-bold text-amber-400">L2</span>
              <span
                class="rounded-full bg-amber-500/20 px-2 py-0.5 font-mono text-xs font-medium text-amber-400"
                >ADVISORY</span
              >
            </div>
            <h3 class="mt-1 font-semibold text-white">
              Semantic similarity against incident history
            </h3>
            <p class="mt-1 text-sm text-white/60">
              Code that resembles past incidents gets flagged with full context: what went wrong,
              when, and how to fix it. Advisory, not blocking — devs decide.
            </p>
          </div>
        </div>

        <!-- L3 — Auto-synthesis -->
        <div class="flex gap-5">
          <div class="flex shrink-0 flex-col items-center">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-500/15">
              <Sparkles class="h-5 w-5 text-violet-400" />
            </div>
          </div>
          <div class="flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="font-mono text-xs font-bold text-violet-400">L3</span>
              <span
                class="rounded-full bg-violet-500/20 px-2 py-0.5 font-mono text-xs font-medium text-violet-400"
                >PROGRESSIVE</span
              >
            </div>
            <h3 class="mt-1 font-semibold text-white">
              LLM-generated rules from new incident patterns
            </h3>
            <p class="mt-1 text-sm text-white/60">
              When the RAG layer catches something without an existing rule, the synthesis engine
              proposes a new Semgrep rule. Reviewed by engineers, promoted to L1.
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ─────────────────────────────────────────────────────── STATS -->
  <section class="border-t border-white/5 py-24">
    <div class="mx-auto max-w-5xl px-6">
      <div class="grid gap-12 text-center sm:grid-cols-3">
        {#each [{ value: '10+', label: 'Incident categories covered', sub: 'regex, injection, race conditions, and more' }, { value: '3', label: 'Detection layers', sub: 'from blocking to progressive synthesis' }, { value: '0', label: 'Repeated incidents', sub: 'once a rule is in place' }] as stat}
          <div>
            <p class="text-5xl font-bold text-white">{stat.value}</p>
            <p class="mt-2 font-medium text-white/80">{stat.label}</p>
            <p class="mt-1 text-sm text-white/50">{stat.sub}</p>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <!-- ─────────────────────────────────────────────────────── BOTTOM CTA -->
  <section class="border-t border-white/5 py-24">
    <div class="mx-auto max-w-2xl px-6 text-center">
      <h2 class="text-3xl font-bold text-white sm:text-4xl">
        Ready to close the loop on incidents?
      </h2>
      <p class="mt-4 text-white/70">
        Join the private beta. We're onboarding engineering teams one by one.
      </p>
      <a
        href="#waitlist"
        class="mt-8 inline-block rounded-lg bg-violet-600 px-8 py-3 text-sm font-semibold text-white transition hover:bg-violet-500"
      >
        Join the waitlist
      </a>
    </div>
  </section>

  <!-- ─────────────────────────────────────────────────────── FOOTER -->
  <footer class="border-t border-white/5 py-10">
    <div
      class="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 text-sm text-white/50"
    >
      <span class="font-mono">oute.muscle</span>
      <div class="flex gap-6">
        <a href="/privacy" class="transition hover:text-white/70">Privacy Policy</a>
        <a href="/terms" class="transition hover:text-white/70">Terms of Service</a>
        <a href="mailto:contact@oute.pro" class="transition hover:text-white/70">Contact</a>
      </div>
      <span>© 2026 Oute. All rights reserved.</span>
    </div>
  </footer>
</main>
