<script lang="ts">
  /**
   * Landing page — oute.me
   * Dark, developer-focused, Vercel/Linear aesthetic.
   * Captures beta waitlist emails via POST /v1/waitlist.
   */
  let email = $state('');
  let name = $state('');
  let company = $state('');
  let status: 'idle' | 'loading' | 'success' | 'error' = $state('idle');
  let errorMsg = $state('');

  // API URL — override via PUBLIC_API_URL env var at build time if needed
  const API_BASE = 'https://oute-prod-api-ujzimacvza-uc.a.run.app';

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    if (!email) return;
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
      class="rounded-md border border-violet-500/40 bg-violet-500/10 px-4 py-1.5 text-sm font-medium text-violet-300 transition hover:bg-violet-500/20"
    >
      Request access
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
      class="pointer-events-none absolute top-0 left-1/2 -translate-x-1/2 h-[500px] w-[700px] rounded-full bg-violet-600/10 blur-[120px]"
    ></div>

    <div class="relative mx-auto max-w-4xl px-6 text-center">
      <div
        class="mb-6 inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-4 py-1.5 text-xs font-medium text-violet-300"
      >
        <span class="inline-block h-1.5 w-1.5 rounded-full bg-violet-400 animate-pulse"></span>
        Private beta — limited access
      </div>

      <h1 class="text-5xl font-bold tracking-tight text-white sm:text-6xl lg:text-7xl">
        Stop repeating<br />
        <span
          class="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent"
        >
          production incidents
        </span>
      </h1>

      <p class="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-white/50">
        Oute Muscle turns your post-mortems into code guardrails. Every incident becomes a
        detection rule that blocks the same mistake from ever reaching production again.
      </p>

      <!-- CTA form -->
      <div id="waitlist" class="mx-auto mt-12 max-w-md scroll-mt-24">
        {#if status === 'success'}
          <div
            class="rounded-xl border border-green-500/30 bg-green-500/10 px-6 py-8 text-center"
          >
            <p class="text-2xl">🎉</p>
            <p class="mt-2 font-semibold text-green-400">You're on the list!</p>
            <p class="mt-1 text-sm text-white/50">We'll reach out as soon as a spot opens up.</p>
          </div>
        {:else}
          <form onsubmit={handleSubmit} class="space-y-3">
            <input
              type="email"
              bind:value={email}
              required
              placeholder="you@company.com"
              class="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-white/30 focus:border-violet-500/60 focus:outline-none focus:ring-1 focus:ring-violet-500/30"
            />
            <div class="flex gap-3">
              <input
                type="text"
                bind:value={name}
                placeholder="Your name (optional)"
                class="flex-1 rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-white/30 focus:border-violet-500/60 focus:outline-none focus:ring-1 focus:ring-violet-500/30"
              />
              <input
                type="text"
                bind:value={company}
                placeholder="Company (optional)"
                class="flex-1 rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-white/30 focus:border-violet-500/60 focus:outline-none focus:ring-1 focus:ring-violet-500/30"
              />
            </div>

            {#if status === 'error'}
              <p class="text-sm text-red-400">{errorMsg}</p>
            {/if}

            <button
              type="submit"
              disabled={status === 'loading'}
              class="w-full rounded-lg bg-violet-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
            >
              {status === 'loading' ? 'Sending...' : 'Request early access →'}
            </button>
          </form>
          <p class="mt-3 text-xs text-white/30">No spam. Invite-only beta. Unsubscribe anytime.</p>
        {/if}
      </div>
    </div>
  </section>

  <!-- ─────────────────────────────────────────────────────── PROBLEM -->
  <section class="border-t border-white/5 py-24">
    <div class="mx-auto max-w-5xl px-6">
      <p class="text-center font-mono text-xs uppercase tracking-widest text-white/30">The problem</p>
      <h2 class="mt-4 text-center text-3xl font-bold text-white sm:text-4xl">
        Every team has a graveyard of avoidable incidents
      </h2>
      <p class="mx-auto mt-4 max-w-2xl text-center text-white/50">
        You write the post-mortem, add an action item, and move on. Three sprints later, a new
        engineer makes the same mistake. The incident repeats. The post-mortem is forgotten.
      </p>

      <div class="mt-16 grid gap-6 sm:grid-cols-3">
        {#each [
          { emoji: '📄', title: 'Post-mortem written', desc: 'Root cause documented. Action items created. Filed away and forgotten.' },
          { emoji: '⏳', title: '3 sprints later', desc: 'New engineer joins. Same pattern coded. Same regex. Same race condition.' },
          { emoji: '🔥', title: 'Incident repeats', desc: 'Same alert fires. Same on-call woken. Same post-mortem written.' }
        ] as item}
          <div class="rounded-xl border border-white/8 bg-white/3 p-6">
            <p class="text-3xl">{item.emoji}</p>
            <p class="mt-3 font-semibold text-white">{item.title}</p>
            <p class="mt-1 text-sm text-white/50">{item.desc}</p>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <!-- ─────────────────────────────────────────────────────── HOW IT WORKS -->
  <section class="border-t border-white/5 py-24">
    <div class="mx-auto max-w-5xl px-6">
      <p class="text-center font-mono text-xs uppercase tracking-widest text-white/30">How it works</p>
      <h2 class="mt-4 text-center text-3xl font-bold text-white sm:text-4xl">
        Three layers. One goal: incidents that never repeat.
      </h2>

      <div class="mt-16 space-y-4">
        {#each [
          {
            layer: 'L1',
            label: 'Static guardrails',
            color: 'text-red-400',
            border: 'border-red-500/20',
            bg: 'bg-red-500/5',
            badge: 'BLOCKING',
            badgeColor: 'bg-red-500/20 text-red-400',
            title: 'Semgrep rules synthesized from incidents',
            desc: 'Every post-mortem automatically becomes a Semgrep rule. The pattern that caused the incident is blocked at CI time — before the PR even lands.'
          },
          {
            layer: 'L2',
            label: 'RAG advisory',
            color: 'text-amber-400',
            border: 'border-amber-500/20',
            bg: 'bg-amber-500/5',
            badge: 'ADVISORY',
            badgeColor: 'bg-amber-500/20 text-amber-400',
            title: 'Semantic similarity against incident history',
            desc: 'Code that resembles past incidents gets flagged with full context: what went wrong, when, and how to fix it. Advisory, not blocking — devs decide.'
          },
          {
            layer: 'L3',
            label: 'Auto-synthesis',
            color: 'text-violet-400',
            border: 'border-violet-500/20',
            bg: 'bg-violet-500/5',
            badge: 'PROGRESSIVE',
            badgeColor: 'bg-violet-500/20 text-violet-400',
            title: 'LLM-generated rules from new incident patterns',
            desc: 'When the RAG layer catches something without an existing rule, the synthesis engine proposes a new Semgrep rule. Reviewed by engineers, promoted to L1.'
          }
        ] as item}
          <div class="flex gap-6 rounded-xl border {item.border} {item.bg} p-6">
            <div class="shrink-0 pt-0.5">
              <span class="font-mono text-xs font-bold {item.color}">{item.layer}</span>
            </div>
            <div class="flex-1">
              <div class="flex flex-wrap items-center gap-3">
                <span class="font-semibold text-white">{item.title}</span>
                <span class="rounded-full px-2 py-0.5 text-xs font-mono font-medium {item.badgeColor}">
                  {item.badge}
                </span>
              </div>
              <p class="mt-1 text-sm text-white/50">{item.desc}</p>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <!-- ─────────────────────────────────────────────────────── STATS -->
  <section class="border-t border-white/5 py-24">
    <div class="mx-auto max-w-5xl px-6">
      <div class="grid gap-12 text-center sm:grid-cols-3">
        {#each [
          { value: '10+', label: 'Incident categories covered', sub: 'regex, injection, race conditions, and more' },
          { value: '3', label: 'Detection layers', sub: 'from blocking to progressive synthesis' },
          { value: '0', label: 'Repeated incidents', sub: 'once a rule is in place' }
        ] as stat}
          <div>
            <p class="text-5xl font-bold text-white">{stat.value}</p>
            <p class="mt-2 font-medium text-white/80">{stat.label}</p>
            <p class="mt-1 text-sm text-white/40">{stat.sub}</p>
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
      <p class="mt-4 text-white/50">
        Join the private beta. We're onboarding engineering teams one by one.
      </p>
      <a
        href="#waitlist"
        class="mt-8 inline-block rounded-lg bg-violet-600 px-8 py-3 text-sm font-semibold text-white transition hover:bg-violet-500"
      >
        Get early access →
      </a>
    </div>
  </section>

  <!-- ─────────────────────────────────────────────────────── FOOTER -->
  <footer class="border-t border-white/5 py-10">
    <div class="mx-auto max-w-6xl px-6 flex items-center justify-between text-sm text-white/30">
      <span class="font-mono">oute.muscle</span>
      <span>© 2026 Oute. All rights reserved.</span>
    </div>
  </footer>
</main>
