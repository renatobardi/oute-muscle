<script lang="ts">
  /**
   * Landing page — muscle.oute.pro
   * Cybersecurity dark theme with neon green accents.
   * "The Loop" pipeline visual + beta waitlist capture.
   */
  let email = $state('');
  let name = $state('');
  let company = $state('');
  let status: 'idle' | 'loading' | 'success' | 'error' = $state('idle');
  let errorMsg = $state('');
  let emailError = $state('');
  let step: 1 | 2 = $state(1);

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
  <title>Oute Muscle — Don't let history repeat itself in your code</title>
  <meta
    name="description"
    content="Analyze past incidents to forge future prevention. Oute Muscle's three-layer detection system converts post-mortems into actionable security rules."
  />
</svelte:head>

<main class="landing">
  <!-- NAV -->
  <nav class="landing-nav">
    <div class="landing-nav-inner">
      <span class="landing-logo">
        Oute<span class="landing-logo-bolt">&#9889;</span><span class="landing-logo-muscle"
          >Muscle</span
        >
      </span>
    </div>
  </nav>

  <!-- HERO -->
  <section class="landing-hero">
    <div class="landing-circuit-bg"></div>

    <div class="landing-hero-content">
      <h1 class="landing-headline">Don't let history repeat itself in your code</h1>

      <p class="landing-subheadline">
        Analyze past incidents to forge future prevention. Oute Muscle's three-layer detection
        system converts post-mortems into actionable security rules, breaking the cycle of
        production failures.
      </p>
    </div>
  </section>

  <!-- THE LOOP -->
  <section class="landing-loop-section">
    <div class="landing-loop-container">
      <h2 class="landing-loop-title">The Loop</h2>

      <div class="landing-pipeline">
        <!-- Post-Mortem Input -->
        <div class="pipeline-node pipeline-input">
          <div class="pipeline-node-label pipeline-label-red">
            <span class="pipeline-icon">&#9888;</span>
            Post-Mortem URL
          </div>
          <div class="pipeline-node-sub">jira.com/browse/INC-396:<br />SQL Injection Report</div>
        </div>

        <!-- L1 -->
        <div class="pipeline-connector connector-red"></div>
        <div class="pipeline-layer">
          <div class="pipeline-layer-badge layer-red">L1</div>
          <div class="pipeline-layer-body layer-body-red">
            <div class="pipeline-layer-label">Detected:<br />Unsanitized Input</div>
          </div>
          <div class="pipeline-layer-sub">Detected:<br />Unsanitized Input Pattern</div>
        </div>

        <!-- L2 -->
        <div class="pipeline-connector connector-blue"></div>
        <div class="pipeline-layer">
          <div class="pipeline-layer-badge layer-blue">L2</div>
          <div class="pipeline-layer-body layer-body-blue">
            <div class="pipeline-layer-label">Detected:<br />Unsanitized Input</div>
          </div>
          <div class="pipeline-layer-sub">Network Traffic<br />Analysis</div>
        </div>

        <!-- L3 -->
        <div class="pipeline-connector connector-green"></div>
        <div class="pipeline-layer">
          <div class="pipeline-layer-badge layer-green">L3</div>
          <div class="pipeline-layer-body layer-body-green">
            <div class="pipeline-layer-label">Anomalous<br />Behavior</div>
          </div>
          <div class="pipeline-layer-sub">Anomalous Behavior<br />Detection</div>
        </div>

        <!-- Security Rule Output -->
        <div class="pipeline-connector connector-green"></div>
        <div class="pipeline-node pipeline-output">
          <div class="pipeline-node-label pipeline-label-green">
            <span class="pipeline-icon">&#10003;</span>
            Security Rule
          </div>
          <div class="pipeline-node-sub">
            New Rule:<br />Block recursive SQL calls<br />on user-controlled inputs
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- REQUEST BETA ACCESS -->
  <section id="waitlist" class="landing-cta-section">
    <h2 class="landing-cta-title">Request Beta Access</h2>

    <div class="landing-cta-form-wrapper">
      {#if status === 'success'}
        <div class="landing-success">
          <p class="landing-success-title">You're on the list!</p>
          <p class="landing-success-sub">We'll reach out as soon as a spot opens up.</p>
        </div>
      {:else if step === 1}
        <form onsubmit={handleSubmit} class="landing-form-inline">
          <input
            type="email"
            bind:value={email}
            onblur={() => {
              if (email) validateEmail();
            }}
            required
            placeholder="Enter your work email..."
            aria-label="Email address"
            aria-describedby={emailError ? 'email-error' : undefined}
            aria-invalid={emailError ? 'true' : undefined}
            class="landing-input {emailError ? 'landing-input-error' : ''}"
          />
          <button type="submit" class="landing-btn">Request Beta Access</button>
        </form>

        {#if emailError}
          <p id="email-error" class="landing-error-msg">{emailError}</p>
        {/if}

        {#if status === 'error'}
          <p class="landing-error-msg">{errorMsg}</p>
        {/if}
      {:else}
        <form onsubmit={handleSubmit} class="landing-form-stack">
          <p class="landing-form-hint">
            Almost there! Tell us a bit more <span class="landing-form-optional">(optional)</span>
          </p>
          <input
            type="text"
            bind:value={name}
            placeholder="Your name"
            aria-label="Your name"
            class="landing-input"
          />
          <input
            type="text"
            bind:value={company}
            placeholder="Company"
            aria-label="Company"
            class="landing-input"
          />

          {#if status === 'error'}
            <p class="landing-error-msg">{errorMsg}</p>
          {/if}

          <button
            type="submit"
            disabled={status === 'loading'}
            class="landing-btn landing-btn-full"
          >
            {status === 'loading' ? 'Sending...' : 'Complete sign-up'}
          </button>
          <button
            type="button"
            onclick={handleSkip}
            disabled={status === 'loading'}
            class="landing-skip-btn"
          >
            Skip — just add me to the list
          </button>
        </form>
      {/if}
    </div>
  </section>

  <!-- FOOTER -->
  <footer class="landing-footer">
    <div class="landing-footer-inner">
      <span class="landing-footer-brand">oute.muscle</span>
      <div class="landing-footer-links">
        <a href="/privacy">Privacy Policy</a>
        <a href="/terms">Terms of Service</a>
        <a href="mailto:contact@oute.pro">Contact</a>
      </div>
      <span class="landing-footer-copy">&copy; 2026 Oute. All rights reserved.</span>
    </div>
  </footer>
</main>

<style>
  /* ── Base ───────────────────────────────────────── */
  .landing {
    min-height: 100vh;
    background: #060b11;
    color: #fff;
    font-family:
      'Inter',
      -apple-system,
      BlinkMacSystemFont,
      'Segoe UI',
      sans-serif;
  }

  /* ── Circuit board background ──────────────────── */
  .landing-circuit-bg {
    position: absolute;
    inset: 0;
    opacity: 0.07;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cdefs%3E%3Cpattern id='circuit' width='200' height='200' patternUnits='userSpaceOnUse'%3E%3Cpath d='M0 100h40M60 100h80M160 100h40M100 0v40M100 60v80M100 160v40' stroke='%2322c55e' stroke-width='1' fill='none'/%3E%3Ccircle cx='50' cy='100' r='4' fill='%2322c55e'/%3E%3Ccircle cx='150' cy='100' r='4' fill='%2322c55e'/%3E%3Ccircle cx='100' cy='50' r='4' fill='%2322c55e'/%3E%3Ccircle cx='100' cy='150' r='4' fill='%2322c55e'/%3E%3Cpath d='M50 50h20v20M130 50h20v20M50 130h20v20M130 130h20v20' stroke='%2322c55e' stroke-width='0.8' fill='none'/%3E%3C/pattern%3E%3C/defs%3E%3Crect width='200' height='200' fill='url(%23circuit)'/%3E%3C/svg%3E");
    pointer-events: none;
  }

  /* ── Nav ────────────────────────────────────────── */
  .landing-nav {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 50;
    padding: 1rem 1.5rem;
    background: rgba(6, 11, 17, 0.85);
    backdrop-filter: blur(12px);
  }

  .landing-nav-inner {
    max-width: 72rem;
    margin: 0 auto;
    display: flex;
    align-items: center;
  }

  .landing-logo {
    font-family: 'Inter', sans-serif;
    font-size: 1.25rem;
    font-weight: 700;
    color: #fff;
    letter-spacing: -0.02em;
  }

  .landing-logo-bolt {
    color: #22c55e;
    margin: 0 -0.05em;
    font-size: 1rem;
  }

  .landing-logo-muscle {
    color: #22c55e;
  }

  /* ── Hero ───────────────────────────────────────── */
  .landing-hero {
    position: relative;
    overflow: hidden;
    padding: 10rem 1.5rem 4rem;
    text-align: center;
  }

  .landing-hero-content {
    position: relative;
    max-width: 48rem;
    margin: 0 auto;
  }

  .landing-headline {
    font-size: clamp(2.5rem, 6vw, 4rem);
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.02em;
    color: #fff;
  }

  .landing-subheadline {
    margin-top: 1.5rem;
    font-size: 1.05rem;
    line-height: 1.7;
    color: rgba(255, 255, 255, 0.55);
    max-width: 40rem;
    margin-left: auto;
    margin-right: auto;
  }

  /* ── The Loop section ──────────────────────────── */
  .landing-loop-section {
    padding: 2rem 1.5rem 5rem;
  }

  .landing-loop-container {
    max-width: 48rem;
    margin: 0 auto;
    border: 1px solid rgba(34, 197, 94, 0.25);
    border-radius: 1rem;
    background: linear-gradient(135deg, rgba(6, 11, 17, 0.95), rgba(10, 20, 15, 0.9));
    padding: 2.5rem 2rem;
    position: relative;
    overflow: hidden;
    box-shadow:
      0 0 60px rgba(34, 197, 94, 0.05),
      inset 0 1px 0 rgba(34, 197, 94, 0.1);
  }

  .landing-loop-container::before {
    content: '';
    position: absolute;
    inset: 0;
    opacity: 0.04;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cdefs%3E%3Cpattern id='c2' width='200' height='200' patternUnits='userSpaceOnUse'%3E%3Cpath d='M0 100h40M60 100h80M160 100h40M100 0v40M100 60v80M100 160v40' stroke='%2322c55e' stroke-width='1' fill='none'/%3E%3Ccircle cx='50' cy='100' r='3' fill='%2322c55e'/%3E%3Ccircle cx='150' cy='100' r='3' fill='%2322c55e'/%3E%3Ccircle cx='100' cy='50' r='3' fill='%2322c55e'/%3E%3Ccircle cx='100' cy='150' r='3' fill='%2322c55e'/%3E%3C/pattern%3E%3C/defs%3E%3Crect width='200' height='200' fill='url(%23c2)'/%3E%3C/svg%3E");
    pointer-events: none;
  }

  .landing-loop-title {
    text-align: center;
    font-size: 1.35rem;
    font-weight: 700;
    color: #fff;
    margin-bottom: 2rem;
    position: relative;
  }

  /* ── Pipeline ──────────────────────────────────── */
  .landing-pipeline {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    overflow-x: auto;
    padding: 1rem 0;
    position: relative;
  }

  .pipeline-node {
    flex-shrink: 0;
    padding: 0.75rem 1rem;
    border-radius: 0.5rem;
    text-align: center;
    min-width: 120px;
  }

  .pipeline-node-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
    padding: 0.4rem 0.75rem;
    border-radius: 0.375rem;
    margin-bottom: 0.5rem;
  }

  .pipeline-label-red {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.4);
    color: #f87171;
    box-shadow: 0 0 12px rgba(239, 68, 68, 0.15);
  }

  .pipeline-label-green {
    background: rgba(34, 197, 94, 0.15);
    border: 1px solid rgba(34, 197, 94, 0.4);
    color: #4ade80;
    box-shadow: 0 0 12px rgba(34, 197, 94, 0.15);
  }

  .pipeline-icon {
    font-size: 0.8rem;
  }

  .pipeline-node-sub {
    font-size: 0.6rem;
    color: rgba(255, 255, 255, 0.4);
    line-height: 1.4;
  }

  .pipeline-connector {
    width: 2rem;
    height: 2px;
    flex-shrink: 0;
    position: relative;
  }

  .connector-red {
    background: linear-gradient(90deg, #ef4444, #f59e0b);
    box-shadow: 0 0 8px rgba(239, 68, 68, 0.3);
  }

  .connector-blue {
    background: linear-gradient(90deg, #3b82f6, #22c55e);
    box-shadow: 0 0 8px rgba(59, 130, 246, 0.3);
  }

  .connector-green {
    background: linear-gradient(90deg, #22c55e, #4ade80);
    box-shadow: 0 0 8px rgba(34, 197, 94, 0.3);
  }

  .pipeline-layer {
    flex-shrink: 0;
    text-align: center;
    position: relative;
  }

  .pipeline-layer-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    border-radius: 0.5rem;
    font-size: 0.7rem;
    font-weight: 800;
    margin-bottom: 0.5rem;
    position: relative;
    z-index: 1;
  }

  .layer-red {
    background: rgba(239, 68, 68, 0.2);
    border: 1px solid rgba(239, 68, 68, 0.5);
    color: #f87171;
    box-shadow: 0 0 16px rgba(239, 68, 68, 0.25);
  }

  .layer-blue {
    background: rgba(59, 130, 246, 0.2);
    border: 1px solid rgba(59, 130, 246, 0.5);
    color: #60a5fa;
    box-shadow: 0 0 16px rgba(59, 130, 246, 0.25);
  }

  .layer-green {
    background: rgba(34, 197, 94, 0.2);
    border: 1px solid rgba(34, 197, 94, 0.5);
    color: #4ade80;
    box-shadow: 0 0 16px rgba(34, 197, 94, 0.25);
  }

  .pipeline-layer-body {
    width: 5rem;
    height: 3.5rem;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 0.5rem;
  }

  .layer-body-red {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.12), rgba(239, 68, 68, 0.04));
    border: 1px solid rgba(239, 68, 68, 0.2);
  }

  .layer-body-blue {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(59, 130, 246, 0.04));
    border: 1px solid rgba(59, 130, 246, 0.2);
  }

  .layer-body-green {
    background: linear-gradient(135deg, rgba(34, 197, 94, 0.12), rgba(34, 197, 94, 0.04));
    border: 1px solid rgba(34, 197, 94, 0.2);
  }

  .pipeline-layer-label {
    font-size: 0.5rem;
    color: rgba(255, 255, 255, 0.5);
    line-height: 1.3;
  }

  .pipeline-layer-sub {
    font-size: 0.55rem;
    color: rgba(255, 255, 255, 0.35);
    line-height: 1.3;
  }

  /* ── CTA Section ───────────────────────────────── */
  .landing-cta-section {
    padding: 4rem 1.5rem 6rem;
    text-align: center;
  }

  .landing-cta-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: #fff;
    margin-bottom: 1.5rem;
  }

  .landing-cta-form-wrapper {
    max-width: 36rem;
    margin: 0 auto;
  }

  .landing-form-inline {
    display: flex;
    gap: 0.5rem;
  }

  .landing-form-stack {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .landing-input {
    flex: 1;
    padding: 0.875rem 1rem;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(34, 197, 94, 0.3);
    border-radius: 0.5rem;
    color: #fff;
    font-size: 0.875rem;
    outline: none;
    transition: border-color 0.2s;
  }

  .landing-input::placeholder {
    color: rgba(255, 255, 255, 0.35);
  }

  .landing-input:focus {
    border-color: rgba(34, 197, 94, 0.6);
    box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.1);
  }

  .landing-input-error {
    border-color: rgba(239, 68, 68, 0.6) !important;
  }

  .landing-btn {
    flex-shrink: 0;
    padding: 0.875rem 1.5rem;
    background: transparent;
    border: 1px solid rgba(34, 197, 94, 0.6);
    border-radius: 0.5rem;
    color: #4ade80;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }

  .landing-btn:hover {
    background: rgba(34, 197, 94, 0.1);
    border-color: #4ade80;
    box-shadow: 0 0 20px rgba(34, 197, 94, 0.15);
  }

  .landing-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .landing-btn-full {
    width: 100%;
  }

  .landing-skip-btn {
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.4);
    font-size: 0.875rem;
    cursor: pointer;
    padding: 0.5rem;
    transition: color 0.2s;
  }

  .landing-skip-btn:hover {
    color: rgba(255, 255, 255, 0.6);
  }

  .landing-skip-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .landing-form-hint {
    font-size: 0.875rem;
    color: rgba(255, 255, 255, 0.5);
  }

  .landing-form-optional {
    color: rgba(255, 255, 255, 0.3);
  }

  .landing-error-msg {
    font-size: 0.875rem;
    color: #f87171;
    margin-top: 0.5rem;
    text-align: left;
  }

  .landing-success {
    border: 1px solid rgba(34, 197, 94, 0.3);
    background: rgba(34, 197, 94, 0.08);
    border-radius: 0.75rem;
    padding: 1.5rem 2rem;
  }

  .landing-success-title {
    font-weight: 600;
    color: #4ade80;
    font-size: 1.1rem;
  }

  .landing-success-sub {
    margin-top: 0.25rem;
    font-size: 0.875rem;
    color: rgba(255, 255, 255, 0.5);
  }

  /* ── Footer ────────────────────────────────────── */
  .landing-footer {
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    padding: 2.5rem 1.5rem;
  }

  .landing-footer-inner {
    max-width: 72rem;
    margin: 0 auto;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    font-size: 0.875rem;
    color: rgba(255, 255, 255, 0.4);
  }

  .landing-footer-brand {
    font-family: monospace;
  }

  .landing-footer-links {
    display: flex;
    gap: 1.5rem;
  }

  .landing-footer-links a {
    color: rgba(255, 255, 255, 0.4);
    text-decoration: none;
    transition: color 0.2s;
  }

  .landing-footer-links a:hover {
    color: rgba(255, 255, 255, 0.6);
  }

  .landing-footer-copy {
    color: rgba(255, 255, 255, 0.3);
  }

  /* ── Responsive ────────────────────────────────── */
  @media (max-width: 640px) {
    .landing-hero {
      padding-top: 7rem;
      padding-bottom: 2rem;
    }

    .landing-form-inline {
      flex-direction: column;
    }

    .landing-btn {
      width: 100%;
    }

    .landing-pipeline {
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .pipeline-connector {
      width: 1rem;
    }

    .landing-footer-inner {
      flex-direction: column;
      text-align: center;
    }
  }
</style>
