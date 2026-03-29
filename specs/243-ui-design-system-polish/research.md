# Research: UI Design System & Visual Polish

**Feature**: 243-ui-design-system-polish
**Date**: 2026-03-29

## R1: Tailwind CSS v4 + CSS Custom Properties Integration

**Decision**: Define CSS custom properties in `app.css` `:root`, reference via `var()` in `tailwind.config.ts` theme extension.

**Rationale**: Tailwind v4 supports CSS-first configuration natively. The project uses `@tailwindcss/postcss` (v4.2.2) with a JS config file (`tailwind.config.ts`). CSS custom properties defined before Tailwind directives are available to the theme extension. This is the recommended v4 approach for design tokens.

**Implementation detail**: The current `app.css` uses legacy `@tailwind base/components/utilities` directives (which work in v4 via the PostCSS plugin). CSS variables go in a `:root` block before these directives.

**Alternatives considered**:
- Tailwind v4 CSS-only config (`@theme` directive): Requires removing the JS config file entirely. Too disruptive -- the project already has a working `tailwind.config.ts`.
- CSS-in-JS tokens: Not SSR-safe, adds runtime overhead. Rejected.
- Tailwind plugin for tokens: Unnecessary indirection when `var()` in theme config works directly.

## R2: Svelte 5 Component Patterns

**Decision**: Use Svelte 5 runes syntax (`$props()`, `$state()`, `$derived()`) with typed props interfaces. Use `{@render}` for slot content (Svelte 5 snippets).

**Rationale**: The entire codebase already uses Svelte 5 runes (confirmed in dashboard and admin layouts). Components must match this pattern for consistency.

**Key patterns**:
- Props: `let { variant = 'primary', size = 'md', ...rest }: ButtonProps = $props();`
- Typed exports via `interface ButtonProps { variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; ... }`
- Slot content via snippet props: `children: Snippet` for default content
- Class merging: `import { twMerge } from 'tailwind-merge';` (already installed)
- Event forwarding: spread `{...rest}` on the root element

**Alternatives considered**:
- Svelte 4 slot syntax (`<slot>`): Deprecated in Svelte 5. Rejected.
- External prop validation (zod): Over-engineering for UI components. TypeScript types are sufficient.

## R3: lucide-svelte Integration

**Decision**: Add `lucide-svelte` as a dependency. Import individual icons by name.

**Rationale**: lucide-svelte provides tree-shakeable Svelte components for each icon. Only imported icons are bundled. The library is MIT-licensed, actively maintained, and has comprehensive icon coverage for developer tooling UIs (shield, alert-triangle, scan, settings, users, etc.).

**Bundle impact**: Each icon is ~200-400 bytes. Estimated 20-30 unique icons across sidebar + pages = ~6-12KB uncompressed, ~2-4KB gzipped. Well within the 50KB budget.

**Alternatives considered**:
- Heroicons (current admin approach -- inline SVG paths): No Svelte components, verbose, harder to maintain.
- Emoji icons (current dashboard approach): Unprofessional appearance. Spec explicitly rejects this.
- Icon font: Larger bundle (loads all icons), not tree-shakeable. Rejected.

## R4: bits-ui Usage for Complex Primitives

**Decision**: Use bits-ui only for `Dialog` (Modal component) and `Listbox` (Select component). All other components are custom.

**Rationale**: bits-ui 2.16 is already installed (though currently unused). It provides headless, accessible primitives that handle complex interaction patterns (focus trapping, keyboard navigation, ARIA). Reimplementing these correctly is error-prone. For simple components (Button, Badge, Card, Input, Table, etc.), custom implementation is simpler and gives full control over token-based styling.

**Alternatives considered**:
- Full bits-ui usage for all components: Over-constraining. Simple components don't need headless primitives.
- No bits-ui (custom Dialog/Select): High risk of accessibility bugs in focus trapping and keyboard navigation. Rejected.
- shadcn-svelte: Adds too many dependencies and conventions. The project needs lightweight, token-based components.

## R5: Sidebar Mobile Behavior

**Decision**: CSS media query for collapse threshold (`md:` = 768px). Svelte `$state()` for open/close toggle. CSS transition for slide-in animation.

**Rationale**: Pure CSS + minimal JS state. No external animation library needed. The sidebar toggle state is local to the Sidebar component (not a store) since it resets on navigation.

**Key details**:
- Desktop (>= 768px): Sidebar always visible, fixed width (256px / w-64)
- Mobile (< 768px): Sidebar hidden, hamburger button in top bar, slide-in overlay from left with backdrop
- Backdrop click or nav item click closes sidebar
- CSS `transform: translateX()` with `transition` for smooth slide

**Alternatives considered**:
- Svelte transition directives (`transition:slide`): Work but less control over backdrop and body scroll lock.
- No mobile behavior: Spec requires responsive down to 320px (FR-020). Rejected.

## R6: Color Token Architecture

**Decision**: Organize tokens into semantic layers:

1. **Primitive palette** (not exposed as Tailwind classes): raw color values stored in variables like `--palette-indigo-500`
2. **Semantic tokens** (exposed via Tailwind): `--color-primary-500`, `--color-error`, `--color-severity-critical`, etc. Reference primitive palette.
3. **Zone tokens**: `--dark-bg`, `--dark-border`, `--light-bg`, `--light-border` for sidebar vs content area.

**Rationale**: Two-layer indirection means changing the primary color from indigo to violet requires changing only the primitive-to-semantic mapping, not every component. Zone tokens allow the dark sidebar / light content pattern without a full dark mode.

**Alternatives considered**:
- Flat token list (no primitive layer): Works for small palettes but makes bulk color changes harder. Rejected for maintainability.
- Tailwind arbitrary values (`bg-[var(--color-x)]`): Verbose, poor DX. Using `tailwind.config.ts` extension maps tokens to standard class names like `bg-primary-500`.
