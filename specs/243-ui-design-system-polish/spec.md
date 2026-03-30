# Feature Specification: UI Design System & Visual Polish

**Feature Branch**: `243-ui-design-system-polish`
**Created**: 2026-03-29
**Status**: Draft
**Input**: User description: "UI/polish pass across all pages -- Login, Dashboard, Admin Cockpit -- with a design system first approach, absorbing visual intelligence from oute.me but fully independent"

## User Scenarios & Testing *(mandatory)*

### User Story 1 -- Design Tokens & Tailwind Theme Foundation (Priority: P1)

A developer opening app.css and tailwind.config.ts finds a complete visual vocabulary: CSS custom properties for every color (backgrounds, surfaces, borders, primary scale, semantic status/severity), typography scale, spacing, border-radius, and shadows. The Tailwind config extends its theme from these tokens -- no hardcoded indigo-*, gray-*, or any raw color class survives in the codebase. Changing a single CSS variable propagates everywhere. The direction is dark sidebar + light content area (GitHub/GitLab pattern), with tokens prepared for both zones.

**Why this priority**: Everything else depends on this. Without tokens, polishing pages means hardcoding colors 200 times. This is the single-point-of-truth that makes US2--US7 consistent and maintainable.

**Independent Test**: Change --color-primary-500 in app.css from indigo to violet. Every button, badge, active state, and accent across the entire app changes color without touching any other file.

**Acceptance Scenarios**:

1. **Given** a fresh checkout, **When** a developer opens app.css, **Then** they find CSS custom properties organized in sections: dark-zone (sidebar/nav backgrounds, borders), light-zone (content area backgrounds, borders), primary scale (400/500/600), semantic colors (error, warning, success, info), severity mapping (critical, high, medium, low), status mapping (active, inactive, pending, failed), typography, spacing, radius, and shadows.
2. **Given** the Tailwind config, **When** a developer reads tailwind.config.ts, **Then** all color keys reference CSS variables via var() -- no hex literals. The existing brand key is replaced by the full token palette.
3. **Given** the full codebase after migration, **When** searching for hardcoded color classes (indigo-, red-, green-, gray- used as raw colors outside token aliases), **Then** zero results are found -- every color reference uses a token-mapped Tailwind class.
4. **Given** a severity value "critical", **When** rendered by any component, **Then** the color is always --color-severity-critical (red) regardless of which page renders it.

---

### User Story 2 -- Component Library Base (Priority: P1)

A developer building a new page never writes inline Tailwind for common patterns. Instead, they import typed Svelte components from $lib/components/ui/: Button, Badge, Card, Table, Input, Select, Modal, MetricCard, PageHeader, EmptyState, LoadingSkeleton, and IconButton. Each component accepts TypeScript-strict props with sensible defaults, uses only design tokens for styling, and covers all interaction states (default, hover, focus, active, disabled, loading, error). The components are small, composable, and render correctly in SSR.

**Why this priority**: Tied with US1. The tokens are the vocabulary; these components are the grammar. Without them, US3--US7 would mean rewriting the same table markup 8 times.

**Independent Test**: Import `<Button variant="primary" size="md" loading={true} />` in an empty Svelte page. It renders a properly styled button with a spinner, using only CSS token colors, with no additional Tailwind classes needed on the consumer side.

**Acceptance Scenarios**:

1. **Given** the component Button, **When** rendered with variant primary, secondary, ghost, or danger and sizes sm, md, lg, **Then** each combination produces a visually distinct, correctly colored button using token colors. Loading state shows a spinner and disables interaction.
2. **Given** the component Badge, **When** rendered with a severity value (critical/high/medium/low/info) or a status value (active/inactive/pending/failed/running), **Then** the badge auto-maps to the correct token color with a tinted background (15% opacity pattern) and a colored dot indicator. Unknown values fall back to neutral gray.
3. **Given** the component Table, **When** rendered with columns, data, and no data, **Then** it shows sortable headers with visual indicators, hover-highlighted rows when populated, and the EmptyState component with a contextual CTA when empty. A loading state renders LoadingSkeleton rows.
4. **Given** the component Modal, **When** opened, **Then** it traps focus, closes on Escape, renders a backdrop overlay, and prevents body scroll. On mobile viewports (< 640px) it renders full-screen.
5. **Given** the component Input, **When** rendered with an error prop, **Then** it shows a red border (token color), error icon, and error message text below the field. Focus state uses the primary accent ring.
6. **Given** the component MetricCard, **When** rendered with a trend (up/down/neutral), **Then** it shows a directional arrow with semantic color (green up, red down, gray neutral). A highlight variant adds a primary accent border.
7. **Given** any component rendered in SSR (server-side), **When** the page loads without JavaScript, **Then** the component renders correctly with no hydration errors. Verification: `svelte-check` passes AND `grep -r "window\.\|document\." apps/web/src/lib/components/ui/ --include="*.svelte"` returns zero results outside `browser`-guarded blocks.

---

### User Story 3 -- Unified Sidebar & Navigation (Priority: P2)

A user navigating between Dashboard and Admin sees a consistent sidebar: dark background, SVG icons (not emojis), active state with a left accent bar, user footer with email and role badge, and smooth behavior. The same Sidebar component serves both contexts with different navigation items. On viewports below 768px, the sidebar collapses into a hamburger toggle with a slide-in overlay.

**Why this priority**: The sidebar is the first thing users see on every page. Emoji icons signal "prototype," not "product." Unifying navigation creates visual coherence between Dashboard and Admin -- currently two different visual worlds (white sidebar vs dark sidebar, emojis vs SVG paths).

**Independent Test**: Navigate from Dashboard /incidents to Admin /admin. The sidebar maintains the same visual structure (dark bg, SVG icons, accent bar) with only the nav items changing. Then resize the browser below 768px -- the sidebar collapses to a hamburger and slides in on tap.

**Acceptance Scenarios**:

1. **Given** the Dashboard sidebar, **When** rendered, **Then** all navigation items use lucide-svelte SVG icons (no emojis), with labels. Active item has a left accent bar (3px, primary color) and tinted background. Inactive items show muted text with hover state.
2. **Given** the Admin sidebar, **When** rendered, **Then** it uses the same Sidebar component with different items and an admin indicator badge. Visual structure (dark bg, icon style, spacing, user footer) is identical to Dashboard.
3. **Given** a viewport below 768px, **When** the page loads, **Then** the sidebar is hidden and a hamburger icon appears in a top bar. Tapping the hamburger slides the sidebar in from the left as an overlay with a backdrop. Tapping the backdrop or a nav item closes it.
4. **Given** the user footer in the sidebar, **When** rendered, **Then** it shows: avatar placeholder (initials circle), truncated email, role badge (using the Badge component), and a logout button.
5. **Given** the Sidebar component, **When** used by both Dashboard and Admin layouts, **Then** the only difference is the items prop and optional variant prop (for the admin badge). No code duplication.

---

### User Story 4 -- Login Page Polish (Priority: P2)

A user arriving at /auth/login sees a professional, branded page: dark background (matching sidebar zone), a centered card with the Muscle logo and product name, clean input fields with icons, a prominent primary CTA, a Google OAuth button following Google's brand guidelines, and clear visual states for loading and errors. The structure stays the same (email/password + Google OAuth) -- only the visual treatment changes.

**Why this priority**: The login page is the first impression. The current plain white card on gray-50 with generic indigo says nothing about the product. A polished login builds trust before the user even signs in.

**Independent Test**: Load /auth/login. The page shows Muscle branding, inputs have icons (mail, lock), the primary button uses token colors, the Google button looks standard. Submit invalid credentials -- the error appears with red accent and icon. Submit valid credentials -- the button shows a loading spinner and inputs disable.

**Acceptance Scenarios**:

1. **Given** a user loading the login page, **When** the page renders, **Then** the background is dark (matching the sidebar zone tokens), the card has proper elevation (shadow + subtle border), and the Muscle logo with beta badge and product name appear above the form.
2. **Given** the email and password fields, **When** rendered, **Then** each has an icon prefix (mail, lock), uses the Input component from US2, has comfortable height (min 44px), and focus state with primary accent ring.
3. **Given** a form submission with invalid credentials, **When** the server responds, **Then** an error message appears with red accent background (tinted, not solid), an error icon, and descriptive text. The specific Firebase error code is mapped to a human-readable message.
4. **Given** a form submission in progress, **When** the request is pending, **Then** the submit button shows a loading spinner (via Button loading prop), both inputs and the Google button are disabled, and no double-submission is possible.
5. **Given** the Google OAuth button, **When** rendered, **Then** it follows Google's branding guidelines: white background, Google "G" logo, "Continue with Google" text. Not a generic styled button.
6. **Given** a viewport below 640px, **When** the page renders, **Then** the card takes full width with appropriate padding, no horizontal overflow.

---

### User Story 5 -- Dashboard Pages Polish (Priority: P3)

A user navigating Dashboard pages (Incidents, Rules, Scans, Audit, Settings) finds every page using design system components: PageHeader with title and actions, Table with sorting and empty states, Badge for severity/status/category, Card for content areas, proper loading skeletons, and consistent spacing. The visual noise of inline Tailwind disappears -- pages feel authored, not hacked.

**Why this priority**: The dashboard is where users spend 90% of their time. After US1--US4 build the foundation, this story applies it where it matters most. Depends on tokens and components being ready.

**Independent Test**: Open /incidents. The page header uses PageHeader, the filter bar uses Input/Select components, the table uses Table with Badge for severity, an empty state appears if no incidents exist, and loading shows skeletons. All of this uses only token colors -- zero hardcoded classes.

**Acceptance Scenarios**:

1. **Given** the Incidents list page, **When** rendered with data, **Then** it shows: PageHeader ("Incidents", description, "Ingest" action button), filter bar with Input (search) and Select (category, severity) components, Table with sortable columns, Badge for severity and category per row, and pagination controls.
2. **Given** any Dashboard page with no data, **When** rendered, **Then** it shows an EmptyState component with a relevant icon, descriptive title, subtitle, and a CTA button (e.g., "Ingest your first incident").
3. **Given** any Dashboard page in loading state, **When** data is fetching, **Then** LoadingSkeleton components replace the content area -- matching the layout shape (table skeleton for list pages, card skeleton for detail pages).
4. **Given** the Incident detail page (/incidents/[id]), **When** rendered, **Then** it uses Card for content sections, Badge for metadata (severity, category, status), and proper typographic hierarchy (title, section headers, body text all using token sizes).
5. **Given** the Settings page, **When** rendered, **Then** team member management uses Table, role display uses Badge, and the invite modal uses the Modal component with Input fields inside.
6. **Given** all 9 Dashboard pages after migration (incidents list, incident detail, incident ingest, rules, rule candidates, scans, audit, settings, settings/billing), **When** auditing the source code, **Then** no page contains hardcoded color classes -- all styling flows through components and tokens.

---

### User Story 6 -- Admin Cockpit Polish (Priority: P3)

An admin navigating the cockpit (/admin/*) finds a polished operational interface: metric cards with trend indicators, health status with animated dots, user/tenant tables with clear role and plan badges, and the same component consistency as the Dashboard. The admin section retains its operational identity (admin badge, cross-tenant context) while sharing the visual language.

**Why this priority**: Same as US5 -- applies the design system to the remaining pages. Can be parallelized with US5 since they share the same components.

**Independent Test**: Open /admin. The overview shows MetricCard components with trends. Navigate to /admin/users -- the table uses the Table component with Badge for roles. Navigate to /admin/health -- status indicators use animated dots. All using token colors.

**Acceptance Scenarios**:

1. **Given** the Admin overview page, **When** rendered, **Then** the 6 metric cards use the MetricCard component with: label, value, optional trend indicator (up/down with semantic color), and the highlight variant for alert thresholds. LLM usage section uses Card with ProgressBar-style visuals.
2. **Given** the Users page, **When** rendered, **Then** the table uses the Table component, role column uses Badge (admin=purple, editor=blue, viewer=gray), status uses Badge (active=green, inactive=gray), and action dropdowns are styled consistently.
3. **Given** the Tenants page, **When** rendered, **Then** plan tier uses Badge with distinct colors (Free=gray, Pro=blue, Enterprise=purple), and metrics columns (contributors, scans, findings) are right-aligned with mono font.
4. **Given** the Health page, **When** rendered, **Then** healthy metrics show a green dot (static), degraded shows yellow (pulsing), and down shows red (pulsing). Auto-refresh indicator is visible. Manual refresh uses Button ghost variant.
5. **Given** all 7 Admin routes after migration, **When** auditing the source code, **Then** no page contains hardcoded color classes.

---

### User Story 7 -- Basic Responsive Behavior (Priority: P4)

A user accessing the app from a tablet or narrow browser window finds everything functional: sidebar collapses (US3), tables scroll horizontally, card grids restack, modals go full-screen, and nothing overflows the viewport. The experience isn't optimized for mobile -- it's just not broken.

**Why this priority**: Responsive is the final pass. It depends on all components and pages being migrated first. The target audience (developers) uses desktop primarily, but the app shouldn't embarrass itself on a tablet.

**Independent Test**: Open the app at 320px viewport width. Navigate every page. No horizontal overflow, no clipped content, no unreachable interactive elements. Tables scroll, cards stack, modals fill the screen.

**Acceptance Scenarios**:

1. **Given** a viewport of 320px width, **When** navigating any page, **Then** no horizontal scrollbar appears on the body. Content that doesn't fit (tables, wide cards) has its own scroll container.
2. **Given** a card grid (metric cards, tenant cards), **When** the viewport is below 640px, **Then** cards stack into a single column. Between 640px--1024px, they show 2 columns. Above 1024px, 3+ columns.
3. **Given** any interactive element (button, link, input, dropdown), **When** rendered on a touch device, **Then** the touch target is at least 44x44px.
4. **Given** the Modal component on a viewport below 640px, **When** opened, **Then** it renders full-screen with proper padding instead of a centered floating card.
5. **Given** the Table component on a viewport below 768px, **When** the table has more columns than fit, **Then** it scrolls horizontally within its container with a visible scroll indicator (shadow or fade).

---

### Edge Cases

- What happens when a Badge receives an unknown status/severity value? Renders as neutral gray with the raw text. No crash, no blank.
- What happens when a Table receives 0 rows? EmptyState component renders with a contextual message and optional CTA.
- What happens with very long text in table cells? Text truncates with text-overflow: ellipsis and a tooltip on hover shows the full content.
- What happens at exactly 768px viewport? The threshold is < 768px = collapsed, >= 768px = expanded. No ambiguity.
- What happens if lucide-svelte icons fail to load? Icons are bundled (not CDN), so this shouldn't happen. If a specific icon name is wrong, a fallback placeholder square renders.
- What happens with CSS custom properties in browsers that don't support them? Minimum browser target: last 2 major versions of Chrome, Firefox, Safari, Edge. All support CSS custom properties. No fallback needed.
- What happens with SSR? All components must render without window/document access. Token colors are defined in CSS (not JS), so SSR is safe.
- What happens if bits-ui primitives conflict with custom components? bits-ui is used only for complex primitives (Dialog, Dropdown) where reimplementation is wasteful. Custom styling wraps bits-ui, not replaces it.

## Requirements *(mandatory)*

### Functional Requirements

**Design Tokens:**

- **FR-001**: App MUST define CSS custom properties for all visual values: backgrounds (dark-zone, light-zone), primary color scale (400/500/600), semantic colors (error, warning, success, info), severity mapping (critical/high/medium/low/info), status mapping (active/inactive/pending/failed/running), neutrals, typography sizes, spacing, border-radius, and shadows.
- **FR-002**: Tailwind config MUST extend its theme from CSS custom properties using var() -- no hex literals in the config.
- **FR-003**: After migration, the codebase MUST NOT contain hardcoded Tailwind color classes (e.g., indigo-600, red-500, gray-200) outside of token-mapped utilities.
- **FR-004**: Severity values MUST map to consistent colors everywhere: critical = red, high = orange, medium = yellow, low = blue, info = gray.

**Component Library:**

- **FR-005**: Each component MUST accept TypeScript-strict props with sensible defaults.
- **FR-006**: Components MUST use only design token CSS variables for colors -- no hardcoded values.
- **FR-007**: Button MUST support variants (primary, secondary, ghost, danger), sizes (sm, md, lg), and states (loading, disabled).
- **FR-008**: Badge MUST auto-map severity and status values to token colors with a tinted background pattern and dot indicator.
- **FR-009**: Table MUST include empty state, loading skeleton, sortable headers with visual indicators, and hover-highlighted rows.
- **FR-010**: Modal MUST implement focus trap, close on Escape, backdrop overlay, and prevent body scroll.
- **FR-011**: Input MUST support icon prefix, label, error state (red border + icon + message), and focus ring using primary token.
- **FR-012**: MetricCard MUST support trend indicator (up/down/neutral with semantic color) and highlight variant.

**Navigation:**

- **FR-013**: A single Sidebar component MUST serve both Dashboard and Admin with configurable items prop.
- **FR-014**: Sidebar MUST use lucide-svelte SVG icons, not emojis or raw SVG path strings.
- **FR-015**: Sidebar MUST collapse on viewports < 768px with a hamburger toggle and slide-in overlay.
- **FR-016**: Active navigation item MUST show a left accent bar (3px, primary color) and tinted background.

**Login:**

- **FR-017**: Login page MUST display Muscle branding (logo + name + beta badge) above the form.
- **FR-018**: Login form MUST show distinct visual states: default, focus, error, loading, disabled.
- **FR-019**: Google OAuth button MUST follow Google's branding guidelines (white bg, G logo).

**Responsive:**

- **FR-020**: App MUST be functional at viewports >= 320px with no horizontal overflow on the body.
- **FR-021**: Grid layouts MUST adapt columns: 3+ cols (> 1024px), 2 cols (640--1024px), 1 col (< 640px).
- **FR-022**: Interactive elements MUST have touch targets >= 44x44px on viewports < 768px.

**Quality:**

- **FR-023**: All components MUST render correctly in SSR (no window/document access at module level).
- **FR-024**: No functional regressions -- auth flows, API calls, routing, data loading MUST remain intact.
- **FR-025**: bits-ui MUST only be used for complex primitives (Dialog/Dropdown internals), not for basic elements that have custom components.

### Key Entities

- **Design Token**: A CSS custom property defining a visual value (color, size, radius, shadow) consumed by Tailwind config and components.
- **UI Component**: A reusable Svelte component in $lib/components/ui/ with typed props, token-based styling, and SSR compatibility.
- **Sidebar Item**: Configuration object with icon (lucide icon name), label, href, and optional badge for the Sidebar component.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero hardcoded Tailwind color classes remain in the codebase after migration (verifiable via grep).
- **SC-002**: Every repeated UI pattern (table, card, badge, button, modal, input, metric card, page header, empty state, loading skeleton) is extracted as a reusable component.
- **SC-003**: A single Sidebar component serves both Dashboard and Admin layouts. Zero emoji icons remain.
- **SC-004**: Login page displays Muscle branding and all visual states (default, focus, error, loading) are distinctly styled.
- **SC-005**: All 18 pages (9 Dashboard + 7 Admin + register + pending) use design system components for their UI patterns.
- **SC-006**: App is functional at 320px viewport width -- no horizontal overflow, all content reachable.
- **SC-007**: Accessibility score >= 90 on login, dashboard index, and admin index pages.
- **SC-008**: All existing e2e and unit tests pass after migration -- zero functional regressions.

## Assumptions

- Icon library: lucide-svelte (MIT, Svelte-native, good icon coverage for dev tooling UIs).
- bits-ui is already in the project dependencies and will be used minimally for complex primitives (Dialog, Dropdown).
- Dark sidebar + light content is the single visual direction -- no light mode toggle, no full dark mode.
- CSS custom properties browser support is assumed (last 2 versions of Chrome, Firefox, Safari, Edge).
- Firebase Auth flow is untouched -- changes are purely visual.
- No backend/API changes -- this is a frontend-only feature.
- Components live in apps/web/src/lib/components/ui/, not in a separate package.
- Landing page (/) is out of scope -- it already has adequate styling.
- Register page (/auth/register) and pending page (/pending) are in scope -- both use hardcoded color classes that must be migrated to design tokens.
- No Storybook, no visual regression testing -- those are future scope.
- Existing bits-ui integration and Tailwind CSS v4 setup are preserved.
- The current app.css has no custom tokens (only Tailwind directives) and tailwind.config.ts has only a minimal brand color -- the foundation will be built from scratch.
- Currently no $lib/components/ directory exists -- the component library is entirely new.
- The dashboard sidebar currently uses emoji icons and a white background; the admin sidebar uses inline SVG paths and a dark background. Both will be unified.
