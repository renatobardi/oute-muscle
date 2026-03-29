# Tasks: UI Design System & Visual Polish

**Input**: Design documents from `/specs/243-ui-design-system-polish/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Install dependencies and create component directory structure

- [x] T001 Install lucide-svelte dependency in apps/web/package.json
- [x] T002 Create component directory structure at apps/web/src/lib/components/ui/

**Checkpoint**: Directory exists, dependency installed, `npm install` succeeds

---

## Phase 2: Foundation -- Design Tokens (US1)

**Purpose**: Establish the design token system that ALL subsequent work depends on

**⚠️ CRITICAL**: No component or page work can begin until tokens are defined

- [x] T003 [US1] Define CSS custom properties (dark-zone, light-zone, primary scale, semantic colors, severity mapping, status mapping, neutrals, typography, spacing, radius, shadows) in apps/web/src/app.css
- [x] T004 [US1] Update Tailwind theme extension to reference CSS variables via var() -- replace brand hex literals with full token palette in apps/web/tailwind.config.ts
- [x] T005 [US1] Verify token integration by running `cd apps/web && npm run check` (svelte-check must pass)

**Checkpoint**: Tokens defined, Tailwind config uses var() references, no hex literals in config

---

## Phase 3: User Story 1 + 2 -- Component Library (Priority: P1) 🎯 MVP

**Goal**: Build all 12 typed Svelte 5 components using design tokens. Components are testable in isolation.

**Independent Test**: Import `<Button variant="primary" size="md" loading={true} />` in a Svelte page -- it renders correctly with token colors.

### Simple Components (parallelizable)

- [x] T006 [P] [US2] Create Button component (variants: primary/secondary/ghost/danger, sizes: sm/md/lg, loading/disabled states) in apps/web/src/lib/components/ui/Button.svelte
- [x] T007 [P] [US2] Create Badge component (severity/status auto-mapping, tinted bg, dot indicator, neutral fallback) in apps/web/src/lib/components/ui/Badge.svelte
- [x] T008 [P] [US2] Create Card component (padding variants, header snippet slot) in apps/web/src/lib/components/ui/Card.svelte
- [x] T009 [P] [US2] Create IconButton component (ghost/secondary variants, sm/md sizes, aria-label) in apps/web/src/lib/components/ui/IconButton.svelte
- [x] T010 [P] [US2] Create PageHeader component (title, description, actions snippet slot) in apps/web/src/lib/components/ui/PageHeader.svelte
- [x] T011 [P] [US2] Create EmptyState component (icon, title, description, action snippet slot) in apps/web/src/lib/components/ui/EmptyState.svelte
- [x] T012 [P] [US2] Create LoadingSkeleton component (text/card/table-row/circle variants) in apps/web/src/lib/components/ui/LoadingSkeleton.svelte

### Complex Components (depend on simple components)

- [x] T013 [US2] Create Input component (icon prefix, label, error state with icon + message, focus ring) in apps/web/src/lib/components/ui/Input.svelte
- [x] T014 [US2] Create Select component using bits-ui Listbox (label, options, placeholder, disabled) in apps/web/src/lib/components/ui/Select.svelte
- [x] T015 [US2] Create Modal component using bits-ui Dialog (focus trap, Escape close, backdrop, body scroll lock, full-screen < 640px) in apps/web/src/lib/components/ui/Modal.svelte
- [x] T016 [US2] Create MetricCard component (label, value, trend indicator with semantic colors, highlight variant) in apps/web/src/lib/components/ui/MetricCard.svelte
- [x] T017 [US2] Create Table component (sortable headers, hover rows, EmptyState integration, LoadingSkeleton rows, horizontal scroll container) in apps/web/src/lib/components/ui/Table.svelte

### Barrel Export

- [x] T018 [US2] Create barrel export for all components in apps/web/src/lib/components/ui/index.ts
- [x] T019 [US2] Verify all components pass svelte-check and ESLint with `cd apps/web && npm run check && npx eslint src/lib/components/`

**Checkpoint**: All 12 components built, typed, SSR-safe. svelte-check passes. Components ready for page integration.

---

## Phase 3.5: Component Unit Tests (Constitution VII — TDD)

**Purpose**: Unit tests for components with non-trivial logic. Constitution VII mandates TDD and test coverage for new code.

**⚠️ REQUIRED**: Constitution principle VII (Quality Gates) requires tests for new code. These tests validate prop behavior, state transitions, and edge cases — not visual appearance.

- [x] T065 [P] [US2] Create Button unit tests (variant rendering, loading state disables interaction, disabled state, click handler) in apps/web/src/lib/components/ui/Button.test.ts
- [x] T066 [P] [US2] Create Badge unit tests (severity auto-mapping, status auto-mapping, unknown value fallback to neutral, dot indicator presence) in apps/web/src/lib/components/ui/Badge.test.ts
- [x] T067 [P] [US2] Create Table unit tests (empty state rendering, loading skeleton rows, sortable header click toggles direction, hover row class) in apps/web/src/lib/components/ui/Table.test.ts
- [x] T068 [P] [US2] Create Modal unit tests (Escape key closes, backdrop click closes, focus trap activation, body scroll lock) in apps/web/src/lib/components/ui/Modal.test.ts
- [x] T069 [P] [US2] Create Input unit tests (error state renders message + icon, icon prefix renders, focus ring class, label association) in apps/web/src/lib/components/ui/Input.test.ts
- [x] T070 [P] [US2] Create MetricCard unit tests (trend up/down/neutral renders correct arrow + color, highlight variant adds accent border) in apps/web/src/lib/components/ui/MetricCard.test.ts
- [x] T071 [US2] Verify SSR safety: `grep -rn "window\.\|document\." apps/web/src/lib/components/ui/ --include="*.svelte"` returns zero results outside `browser`-guarded blocks (FR-023)
- [x] T072 [US2] Run all component tests: `cd apps/web && npx vitest run src/lib/components/`

**Checkpoint**: 6 component test files created. All tests pass. Zero SSR-unsafe references. Constitution VII satisfied.

---

## Phase 4: User Story 3 -- Unified Sidebar & Navigation (Priority: P2)

**Goal**: Single Sidebar component replaces both Dashboard and Admin sidebars. Lucide icons replace emojis/inline SVGs. Mobile collapse at < 768px.

**Independent Test**: Navigate from /incidents to /admin -- same visual structure, different items. Resize below 768px -- sidebar collapses to hamburger.

- [x] T020 [US3] Create Sidebar component (items prop, variant prop, user footer, lucide icons, active accent bar, mobile hamburger toggle with slide-in overlay and backdrop) in apps/web/src/lib/components/ui/Sidebar.svelte
- [x] T021 [US3] Add Sidebar to barrel export in apps/web/src/lib/components/ui/index.ts
- [x] T022 [US3] Replace Dashboard sidebar with Sidebar component in apps/web/src/routes/(dashboard)/+layout.svelte -- map existing nav items (Incidents, Rules, Scans, Settings, Audit, Rule Synthesis) to SidebarItem[] with lucide icons
- [x] T023 [US3] Replace Admin sidebar with Sidebar component (variant="admin") in apps/web/src/routes/admin/+layout.svelte -- map existing nav items (Overview, Users, Tenants, Health, Incidents, Rules, Access Control) to SidebarItem[] with lucide icons
- [x] T024 [US3] Verify both sidebars render correctly: dark bg, SVG icons, active accent bar, user footer, mobile collapse

- [x] T073 [US3] Create Sidebar unit tests (renders items with icons, active item accent bar, variant="admin" shows admin badge, mobile toggle visibility) in apps/web/src/lib/components/ui/Sidebar.test.ts

**Checkpoint**: Single Sidebar component serves both layouts. Zero emoji icons remain. Mobile sidebar collapses. Sidebar tests pass.

---

## Phase 5: User Story 4 -- Login Page Polish (Priority: P2)

**Goal**: Professional branded login with dark background, Muscle logo, Input/Button components, Google OAuth button styling.

**Independent Test**: Load /auth/login -- Muscle branding visible, inputs have icons, error/loading states work, Google button follows brand guidelines.

- [x] T025 [US4] Polish login page: dark background, centered card with elevation, Muscle logo with beta badge and product name in apps/web/src/routes/auth/login/+page.svelte
- [x] T026 [US4] Replace inline form inputs with Input component (mail icon for email, lock icon for password) in apps/web/src/routes/auth/login/+page.svelte
- [x] T027 [US4] Replace inline submit button with Button component (loading state, disabled during submission) in apps/web/src/routes/auth/login/+page.svelte
- [x] T028 [US4] Style Google OAuth button following Google brand guidelines (white bg, G logo SVG, "Continue with Google" text) in apps/web/src/routes/auth/login/+page.svelte
- [x] T029 [US4] Style error message with tinted red background, error icon, and human-readable Firebase error mapping in apps/web/src/routes/auth/login/+page.svelte
- [x] T030 [US4] Verify login page at 640px and 320px viewport: card takes full width, no overflow

**Checkpoint**: Login shows Muscle branding, all visual states (default, focus, error, loading) are distinct. Google button follows brand guidelines.

---

## Phase 6: User Story 5 -- Dashboard Pages Polish (Priority: P3)

**Goal**: All 9 Dashboard pages use design system components. Zero hardcoded color classes.

**Independent Test**: Open /incidents -- PageHeader, Table with Badge for severity, EmptyState, LoadingSkeleton all present using token colors.

### Dashboard Pages (parallelizable -- different files)

- [x] T031 [P] [US5] Migrate Incidents list page: PageHeader, filter bar (Input + Select), Table with Badge for severity/category, EmptyState, LoadingSkeleton, pagination in apps/web/src/routes/(dashboard)/incidents/+page.svelte
- [x] T032 [P] [US5] Migrate Incident detail page: Card sections, Badge for metadata, typographic hierarchy, delete Modal in apps/web/src/routes/(dashboard)/incidents/[id]/+page.svelte
- [x] T033 [P] [US5] Migrate Incident ingest page: Card, Input fields, Button, form layout in apps/web/src/routes/(dashboard)/incidents/ingest/+page.svelte
- [x] T034 [P] [US5] Migrate Rules list page: PageHeader, Table with Badge, EmptyState in apps/web/src/routes/(dashboard)/rules/+page.svelte
- [x] T035 [P] [US5] Migrate Rule candidates page: PageHeader, Table with Badge, EmptyState in apps/web/src/routes/(dashboard)/rules/candidates/+page.svelte
- [x] T036 [P] [US5] Migrate Scans page: PageHeader, Table with Badge for status, EmptyState, LoadingSkeleton in apps/web/src/routes/(dashboard)/scans/+page.svelte
- [x] T037 [P] [US5] Migrate Audit page: PageHeader, Table, Badge for actions, EmptyState in apps/web/src/routes/(dashboard)/audit/+page.svelte
- [x] T038 [P] [US5] Migrate Settings page: PageHeader, Table for team members, Badge for roles, Modal for invite in apps/web/src/routes/(dashboard)/settings/+page.svelte
- [x] T039 [P] [US5] Migrate Settings/Billing page: Card sections, Badge for plan tier in apps/web/src/routes/(dashboard)/settings/billing/+page.svelte
- [x] T040 [US5] Verify zero hardcoded color classes in Dashboard routes with `grep -r "indigo-\|red-[0-9]\|green-[0-9]\|orange-[0-9]\|gray-[0-9]" apps/web/src/routes/\(dashboard\)/ --include="*.svelte"`

**Checkpoint**: All 9 Dashboard pages use design system components. Zero hardcoded color classes in (dashboard)/ routes.

---

## Phase 7: User Story 6 -- Admin Cockpit Polish (Priority: P3)

**Goal**: All 7 Admin routes use design system components. Zero hardcoded color classes.

**Independent Test**: Open /admin -- MetricCard with trends. /admin/users -- Table with Badge for roles. /admin/health -- animated status dots.

### Admin Pages (parallelizable -- different files)

- [x] T041 [P] [US6] Migrate Admin overview page: MetricCard grid (6 cards with trends + highlight), Card for LLM usage section in apps/web/src/routes/admin/+page.svelte
- [x] T042 [P] [US6] Migrate Users page: Table with Badge for role (admin/editor/viewer) and status (active/inactive), action dropdowns in apps/web/src/routes/admin/users/+page.svelte
- [x] T043 [P] [US6] Migrate Tenants page: Table with Badge for plan tier (Free/Pro/Enterprise), right-aligned mono metrics in apps/web/src/routes/admin/tenants/+page.svelte
- [x] T044 [P] [US6] Migrate Health page: status dots (green static/yellow pulsing/red pulsing), auto-refresh indicator, Button ghost for manual refresh in apps/web/src/routes/admin/health/+page.svelte
- [x] T045 [P] [US6] Migrate Admin incidents page: PageHeader, Table with Badge, EmptyState in apps/web/src/routes/admin/incidents/+page.svelte
- [x] T046 [P] [US6] Migrate Admin rules page: PageHeader, Table with Badge, EmptyState in apps/web/src/routes/admin/rules/+page.svelte
- [x] T047 [P] [US6] Migrate Access control page: PageHeader, Table, Badge, Modal in apps/web/src/routes/admin/access/+page.svelte
- [x] T048 [US6] Verify zero hardcoded color classes in Admin routes with `grep -r "indigo-\|red-[0-9]\|green-[0-9]\|orange-[0-9]\|gray-[0-9]" apps/web/src/routes/admin/ --include="*.svelte"`

**Checkpoint**: All Admin pages use design system components. Zero hardcoded color classes in admin/ routes.

---

## Phase 8: Auth & Auxiliary Pages Polish

**Goal**: Register and pending pages use design system components and token colors.

**Independent Test**: Load /auth/register and /pending -- both use Card, Button, Input components with token colors. No hardcoded indigo-/gray- classes.

- [x] T049 [P] [US5] Migrate Register page: dark background (matching login), Card, Input (company + email), Button, error state, link styling in apps/web/src/routes/auth/register/+page.svelte
- [x] T050 [P] [US5] Migrate Pending approval page: dark background, Card, Button, replace inline SVG with lucide Clock icon, token colors in apps/web/src/routes/pending/+page.svelte
- [x] T051 Verify zero hardcoded color classes in auth and pending routes with `grep -r "indigo-\|red-[0-9]\|green-[0-9]\|orange-[0-9]\|gray-[0-9]" apps/web/src/routes/auth/ apps/web/src/routes/pending/ --include="*.svelte"`

**Checkpoint**: All auth and auxiliary pages use design system components. Zero hardcoded color classes.

---

## Phase 9: User Story 7 -- Responsive & Polish (Priority: P4)

**Goal**: Functional at 320px viewport. No horizontal overflow. Touch targets >= 44px. Accessibility >= 90.

**Independent Test**: Navigate every page at 320px -- no overflow, cards stack, tables scroll, modals go full-screen.

- [x] T052 [US7] Verify sidebar mobile collapse behavior at < 768px across Dashboard and Admin
- [x] T053 [US7] Verify card grids restack: 1 col (< 640px), 2 cols (640-1024px), 3+ cols (> 1024px) on admin overview and dashboard pages
- [x] T054 [US7] Verify Table horizontal scroll with visible scroll indicator on viewports < 768px
- [x] T055 [US7] Verify Modal full-screen rendering on viewports < 640px
- [x] T056 [US7] Audit touch targets >= 44x44px on all interactive elements at mobile viewports
- [ ] T057 [US7] Run Lighthouse accessibility audit on /auth/login, /(dashboard) index, and /admin index -- verify score >= 90 (DEFERRED: requires running app with Firebase ADC — **trigger: run after first successful deploy of this branch to muscle-prod-web on Cloud Run**)
- [x] T058 [US7] Run existing frontend tests: `cd apps/web && npx vitest run`
- [ ] T059 [US7] Run existing e2e tests: `cd apps/web && npx playwright test` (DEFERRED: requires running app with Firebase ADC — **trigger: run after first successful deploy of this branch to muscle-prod-web on Cloud Run**)
- [x] T060 [US7] Run svelte-check and ESLint on full apps/web codebase

**Checkpoint**: All pages functional at 320px. Unit tests pass. No type errors. No lint errors. Deferred: Lighthouse accessibility (T057) and e2e tests (T059) — run post-deploy.

---

## Phase 10: Final Validation

**Purpose**: Cross-cutting verification across all stories

- [x] T061 Verify zero hardcoded Tailwind color classes across entire codebase: `grep -r "indigo-\|red-[0-9]\|green-[0-9]\|orange-[0-9]\|gray-[0-9]" apps/web/src/routes/ --include="*.svelte"` (only landing page / out of scope)
- [x] T062 Verify zero emoji icons remain in sidebar navigation: `grep -r "⚡\|🔒\|🔍\|⚙️" apps/web/src/routes/ --include="*.svelte"`
- [x] T063 Verify token propagation test: mentally confirm that changing --color-primary-500 in app.css would propagate to all buttons, badges, active states
- [x] T064 Run full quality gate: `cd apps/web && npm run check && npx eslint . && npx vitest run`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies -- start immediately
- **Phase 2 (Tokens)**: Depends on Phase 1 -- BLOCKS all component work
- **Phase 3 (Components)**: Depends on Phase 2 -- BLOCKS all page work
- **Phase 3.5 (Component Tests)**: Depends on Phase 3 -- can run parallel with Phase 4/5
- **Phase 4 (Sidebar)**: Depends on Phase 3 (uses Badge, IconButton)
- **Phase 5 (Login)**: Depends on Phase 3 (uses Input, Button) -- can run parallel with Phase 4
- **Phase 6 (Dashboard)**: Depends on Phase 3 + Phase 4 (pages need Sidebar in layout)
- **Phase 7 (Admin)**: Depends on Phase 3 + Phase 4 -- can run parallel with Phase 6
- **Phase 8 (Auth pages)**: Depends on Phase 3 (uses Input, Button, Card) -- can run parallel with Phases 4-7
- **Phase 9 (Responsive)**: Depends on Phases 4-8
- **Phase 10 (Validation)**: Depends on all previous phases

### User Story Dependencies

- **US1 (Tokens)**: No dependencies -- foundational
- **US2 (Components)**: Depends on US1 (tokens must exist)
- **US3 (Sidebar)**: Depends on US2 (uses Badge, IconButton)
- **US4 (Login)**: Depends on US2 (uses Input, Button) -- independent of US3
- **US5 (Dashboard)**: Depends on US2 + US3 (needs components + sidebar)
- **US6 (Admin)**: Depends on US2 + US3 -- can run parallel with US5
- **US7 (Responsive)**: Depends on US3-US6 (needs all pages migrated)

### Parallel Opportunities

Within Phase 3: All 7 simple components (T006-T012) can run in parallel
Within Phase 6: All 9 Dashboard pages (T031-T039) can run in parallel
Within Phase 7: All 7 Admin pages (T041-T047) can run in parallel
Phase 5 (Login) and Phase 4 (Sidebar): Can run in parallel after Phase 3

---

## Parallel Example: Component Library

```bash
# Launch all simple components in parallel (T006-T012):
Task: "Create Button component in apps/web/src/lib/components/ui/Button.svelte"
Task: "Create Badge component in apps/web/src/lib/components/ui/Badge.svelte"
Task: "Create Card component in apps/web/src/lib/components/ui/Card.svelte"
Task: "Create IconButton component in apps/web/src/lib/components/ui/IconButton.svelte"
Task: "Create PageHeader component in apps/web/src/lib/components/ui/PageHeader.svelte"
Task: "Create EmptyState component in apps/web/src/lib/components/ui/EmptyState.svelte"
Task: "Create LoadingSkeleton component in apps/web/src/lib/components/ui/LoadingSkeleton.svelte"
```

## Parallel Example: Dashboard Migration

```bash
# Launch all Dashboard page migrations in parallel (T031-T039):
Task: "Migrate Incidents list in apps/web/src/routes/(dashboard)/incidents/+page.svelte"
Task: "Migrate Incident detail in apps/web/src/routes/(dashboard)/incidents/[id]/+page.svelte"
# ... all 9 pages simultaneously
```

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Tokens (T003-T005)
3. Complete Phase 3: Components (T006-T019)
4. **STOP and VALIDATE**: Components render correctly with token colors
5. This delivers reusable design system -- value even without page migration

### Incremental Delivery

1. Setup + Tokens + Components → Design system ready (MVP)
2. Add Sidebar + Login → Navigation unified, first impression polished
3. Add Dashboard pages → Primary user experience polished
4. Add Admin pages → Full coverage
5. Responsive pass → Quality bar met

### Single Developer Strategy

Execute phases sequentially: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10
Within each phase, execute [P] tasks one by one but in any order.

---

## Notes

- [P] tasks = different files, no dependencies on each other
- [Story] label maps task to specific user story for traceability
- Each phase checkpoint validates the story independently
- Commit after each completed component or page migration
- All components MUST use Svelte 5 runes syntax ($props, $state, $derived)
- All components MUST be SSR-safe (no window/document at module level)
- All color classes MUST use token-mapped Tailwind utilities, never raw color classes
