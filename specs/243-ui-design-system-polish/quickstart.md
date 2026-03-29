# Quickstart: UI Design System & Visual Polish

**Feature**: 243-ui-design-system-polish

## Prerequisites

- Node.js (see `.nvmrc` or package.json engines)
- `npm install` in `apps/web/`

## Development

```bash
# Install new dependency (lucide-svelte)
cd apps/web && npm install lucide-svelte

# Run SvelteKit dev server
make dev-web

# Type check
cd apps/web && npm run check

# Run frontend tests
make test-web

# Lint
cd apps/web && npx eslint .

# Format
cd apps/web && npx prettier --write .
```

## Key Files

| File | Purpose |
|------|---------|
| `apps/web/src/app.css` | Design tokens (CSS custom properties) |
| `apps/web/tailwind.config.ts` | Tailwind theme extension from tokens |
| `apps/web/src/lib/components/ui/*.svelte` | Component library |
| `apps/web/src/lib/components/ui/index.ts` | Barrel export |
| `apps/web/src/routes/(dashboard)/+layout.svelte` | Dashboard layout (uses Sidebar) |
| `apps/web/src/routes/admin/+layout.svelte` | Admin layout (uses Sidebar) |
| `apps/web/src/routes/auth/login/+page.svelte` | Login page |

## Component Usage

```svelte
<script lang="ts">
  import { Button, Badge, Table, Input, PageHeader } from '$components/ui';
  import { Shield } from 'lucide-svelte';
</script>

<PageHeader title="Incidents" description="Manage detected incidents">
  {#snippet actions()}
    <Button variant="primary">Ingest</Button>
  {/snippet}
</PageHeader>

<Input icon={Shield} label="Search" placeholder="Search incidents..." />

<Badge severity="critical" />
<Badge status="active" />
```

## Token Customization

To change the primary color across the entire app, edit `app.css`:

```css
:root {
  --color-primary-400: #a78bfa;  /* violet-400 */
  --color-primary-500: #8b5cf6;  /* violet-500 */
  --color-primary-600: #7c3aed;  /* violet-600 */
}
```

No other files need to change.

## Verification

```bash
# Check for hardcoded color classes (should return 0 results after migration)
grep -r "indigo-\|red-[0-9]\|green-[0-9]\|orange-[0-9]" apps/web/src/routes/ --include="*.svelte" | grep -v "token"

# Run all frontend tests
cd apps/web && npx vitest run

# Run e2e tests
cd apps/web && npx playwright test

# Type check
cd apps/web && npm run check
```
