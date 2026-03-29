# Implementation Plan: UI Design System & Visual Polish

**Branch**: `243-ui-design-system-polish` | **Date**: 2026-03-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/243-ui-design-system-polish/spec.md`

## Summary

Establish a design token system (CSS custom properties) and component library (12 Svelte 5 components) to replace all hardcoded Tailwind color classes across 13 pages. Unify Dashboard and Admin sidebars into a single component with lucide-svelte icons. Polish login page with Muscle branding. Ensure responsive behavior down to 320px. Frontend-only -- no backend/API changes.

## Technical Context

**Language/Version**: TypeScript 5.5+ (strict), Svelte 5, SvelteKit 2.5+
**Primary Dependencies**: Tailwind CSS 4.2 (via @tailwindcss/postcss), bits-ui 2.16 (Dialog/Dropdown only), lucide-svelte (NEW -- to be added)
**Storage**: N/A (frontend-only, no new persistence)
**Testing**: Vitest (unit), Playwright (e2e)
**Target Platform**: Web (SSR via adapter-node on Cloud Run), last 2 versions Chrome/Firefox/Safari/Edge
**Project Type**: SvelteKit web application (monorepo member: apps/web)
**Performance Goals**: No increase in LCP > 200ms; bundle size increase < 50KB gzipped from lucide-svelte tree-shaken icons
**Constraints**: SSR-safe (no window/document at module level), Svelte 5 runes syntax ($state, $props, $derived), Tailwind v4 CSS-first config
**Scale/Scope**: 18 pages (9 Dashboard + 7 Admin + register + pending), 12 new components, ~2600 lines of existing page code to migrate

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Product Mission | PASS | UI polish supports the product dashboard -- no scope drift |
| IV. Architecture & Infrastructure | PASS | Frontend: SvelteKit (mandated). No infra changes. |
| VII. Quality Gates | PASS | ESLint + TypeScript strict + vitest. Existing tests must pass (SC-008). |
| X. Clean Architecture & Hexagonal Boundaries | PASS | Components are UI-layer only, no domain boundary crossing. No speculative abstractions -- bits-ui used only where reimplementation is wasteful (Dialog, Dropdown). |
| XI. Incremental Complexity | PASS | Components built only when needed by actual pages (12 components for 13 pages = justified). No premature abstractions. |
| XII. Observability | N/A | Frontend-only -- no new logging/tracing needed |

No violations. No Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/243-ui-design-system-polish/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (component props/types)
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
apps/web/
├── src/
│   ├── app.css                          # Design tokens (CSS custom properties)
│   ├── lib/
│   │   └── components/
│   │       └── ui/
│   │           ├── Button.svelte
│   │           ├── Badge.svelte
│   │           ├── Card.svelte
│   │           ├── Table.svelte
│   │           ├── Input.svelte
│   │           ├── Select.svelte
│   │           ├── Modal.svelte
│   │           ├── MetricCard.svelte
│   │           ├── PageHeader.svelte
│   │           ├── EmptyState.svelte
│   │           ├── LoadingSkeleton.svelte
│   │           ├── IconButton.svelte
│   │           ├── Sidebar.svelte
│   │           └── index.ts             # Barrel export
│   ├── routes/
│   │   ├── auth/login/+page.svelte      # US4: Login polish
│   │   ├── (dashboard)/
│   │   │   ├── +layout.svelte           # US3: Unified sidebar
│   │   │   ├── incidents/               # US5: Dashboard polish
│   │   │   ├── rules/                   # US5
│   │   │   ├── scans/                   # US5
│   │   │   ├── audit/                   # US5
│   │   │   └── settings/                # US5
│   │   └── admin/
│   │       ├── +layout.svelte           # US3: Unified sidebar
│   │       ├── +page.svelte             # US6: Admin overview
│   │       ├── users/                   # US6
│   │       ├── tenants/                 # US6
│   │       ├── health/                  # US6
│   │       ├── incidents/               # US6
│   │       ├── rules/                   # US6
│   │       └── access/                  # US6
│   └── ...
├── tailwind.config.ts                   # US1: Theme from tokens
└── package.json                         # lucide-svelte dependency
```

**Structure Decision**: All new code lives within the existing `apps/web/` workspace member. Components go in `src/lib/components/ui/` (the `$components` alias is already configured in svelte.config.js). No new packages or workspace members.

## Architecture Decisions

### AD-1: CSS Custom Properties as Token Source

Design tokens are defined as CSS custom properties in `app.css` `:root` scope. Tailwind config references them via `var()`. This approach:
- Works with Tailwind v4's CSS-first configuration
- SSR-safe (CSS variables resolve at render time, not build time)
- Enables future theming without Tailwind config changes
- Single source of truth for all color values

### AD-2: Tailwind v4 Compatibility

The project uses Tailwind v4 with `@tailwindcss/postcss`. Current `app.css` uses legacy `@tailwind` directives which work via the PostCSS plugin. The token system will add CSS custom properties in `:root` before the Tailwind directives. The `tailwind.config.ts` will extend theme colors to reference these variables.

### AD-3: Component Strategy -- Thin Wrappers, Not Framework

Components are thin Svelte 5 wrappers using token-based Tailwind classes. They:
- Use `$props()` runes syntax (Svelte 5)
- Accept typed props with defaults
- Compose via slots/snippets (Svelte 5 `{@render}` pattern)
- Use `tailwind-merge` (already installed) for class merging
- Use bits-ui only for Modal (Dialog primitive) and Select (Dropdown primitive)

### AD-4: Sidebar Unification

One `Sidebar.svelte` component serves both Dashboard and Admin. Differences:
- `items` prop: array of `SidebarItem` objects with lucide icon component reference, label, href
- `variant` prop: optional "admin" adds admin badge
- Both use dark background (unifying the current white Dashboard + dark Admin into one dark style)

### AD-5: Migration Strategy -- Bottom-Up

1. Tokens first (app.css + tailwind.config.ts) -- no visual change yet
2. Components built against tokens -- testable in isolation
3. Sidebar component -- replaces both layout sidebars
4. Login page -- self-contained, uses Input + Button components
5. Dashboard pages -- one by one, replacing inline Tailwind with components
6. Admin pages -- same approach, parallel with Dashboard
7. Responsive pass -- final sweep across all pages

This order minimizes risk: each step builds on the previous, and pages can be migrated incrementally without breaking others.

## Phased Implementation

### Phase 1: Foundation (US1 + US2) -- Tokens & Components

**Goal**: Design token system and full component library, testable in isolation.

1. Install `lucide-svelte` dependency
2. Define CSS custom properties in `app.css` (dark-zone, light-zone, primary, semantic, severity, status, neutrals, typography, spacing, radius, shadows)
3. Update `tailwind.config.ts` to extend theme from CSS variables
4. Build 12 components in `src/lib/components/ui/`:
   - Simple: Button, Badge, Card, IconButton, PageHeader, EmptyState, LoadingSkeleton
   - With bits-ui: Modal (Dialog), Select (Listbox)
   - Complex: Table (sortable headers, empty state, skeleton), Input (icon prefix, error state), MetricCard (trend indicator)
5. Create barrel export `index.ts`

**Exit criteria**: All components render in isolation with correct token colors. `svelte-check` passes.

### Phase 2: Navigation & Login (US3 + US4)

**Goal**: Unified sidebar and polished login page.

1. Build `Sidebar.svelte` with items prop, lucide icons, active accent bar, user footer, mobile collapse
2. Replace Dashboard `+layout.svelte` sidebar with `<Sidebar>` component
3. Replace Admin `+layout.svelte` sidebar with `<Sidebar variant="admin">` component
4. Polish login page: dark background, Muscle branding, Input/Button components, Google OAuth button styling

**Exit criteria**: Dashboard and Admin share Sidebar component. Login shows branding and all visual states. Mobile sidebar collapses.

### Phase 3: Page Migration (US5 + US6)

**Goal**: All 13 pages use design system components, zero hardcoded color classes.

1. Dashboard pages (9): incidents list, incident detail, incident ingest, rules, rules/candidates, scans, audit, settings, settings/billing
2. Admin pages (7): overview, users, tenants, health, incidents, rules, access
3. Each page: replace inline tables with Table, inline badges with Badge, inline cards with Card, add PageHeader, add EmptyState for no-data, add LoadingSkeleton for loading
4. Auth pages: register page (use Input, Button, Card components), pending page (use Card, Button components with token colors)

**Exit criteria**: `grep -r "indigo-\|red-[0-9]\|green-[0-9]\|gray-[0-9]" apps/web/src/routes/` returns zero results (excluding token-mapped utilities).

### Phase 4: Responsive & Polish (US7)

**Goal**: Functional at 320px, no horizontal overflow, touch targets.

1. Verify sidebar mobile behavior (built in Phase 2)
2. Add horizontal scroll containers to Table component
3. Verify card grids restack (1/2/3 column breakpoints)
4. Verify Modal full-screen on mobile
5. Verify touch targets >= 44px
6. Run Lighthouse accessibility audit on /auth/login, /(dashboard), and /admin -- verify score >= 90

**Exit criteria**: No horizontal overflow at 320px. Accessibility score >= 90 on key pages. All existing tests pass.
