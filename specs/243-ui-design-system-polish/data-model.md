# Data Model: UI Design System & Visual Polish

**Feature**: 243-ui-design-system-polish
**Date**: 2026-03-29

This feature has no database changes. The "data model" is the TypeScript type system for component props and design tokens.

## Design Token Types

```typescript
// Severity values (from packages/core domain)
type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

// Status values used across Dashboard and Admin
type Status = 'active' | 'inactive' | 'pending' | 'failed' | 'running';

// Trend direction for MetricCard
type Trend = 'up' | 'down' | 'neutral';
```

## Component Props

### Button
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| variant | 'primary' \| 'secondary' \| 'ghost' \| 'danger' | 'primary' | Visual style |
| size | 'sm' \| 'md' \| 'lg' | 'md' | Size preset |
| loading | boolean | false | Shows spinner, disables interaction |
| disabled | boolean | false | Disables interaction |
| type | 'button' \| 'submit' \| 'reset' | 'button' | HTML button type |
| children | Snippet | required | Button content |

### Badge
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| severity | Severity \| undefined | undefined | Auto-maps to severity color |
| status | Status \| undefined | undefined | Auto-maps to status color |
| label | string | undefined | Text override (falls back to severity/status value) |
| dot | boolean | true | Shows colored dot indicator |

Behavior: If both `severity` and `status` are provided, `severity` takes precedence. Unknown values render as neutral gray.

### Card
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| padding | 'sm' \| 'md' \| 'lg' | 'md' | Internal padding |
| children | Snippet | required | Card content |
| header | Snippet \| undefined | undefined | Optional header slot |

### Table
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| columns | TableColumn[] | required | Column definitions |
| data | Record<string, unknown>[] | [] | Row data |
| loading | boolean | false | Shows skeleton rows |
| skeletonRows | number | 5 | Number of skeleton rows when loading |
| emptyTitle | string | 'No data' | EmptyState title |
| emptyDescription | string | '' | EmptyState description |
| emptyAction | Snippet \| undefined | undefined | EmptyState CTA |
| sortKey | string \| undefined | undefined | Currently sorted column key |
| sortDir | 'asc' \| 'desc' | 'asc' | Sort direction |
| onSort | (key: string) => void | undefined | Sort handler |
| row | Snippet<[Record<string, unknown>]> | undefined | Custom row renderer |

```typescript
interface TableColumn {
  key: string;
  label: string;
  sortable?: boolean;
  align?: 'left' | 'center' | 'right';
  width?: string;
}
```

### Input
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| label | string \| undefined | undefined | Field label |
| type | 'text' \| 'email' \| 'password' \| 'search' \| 'number' | 'text' | Input type |
| placeholder | string | '' | Placeholder text |
| value | string | '' | Bound value |
| error | string \| undefined | undefined | Error message (shows red state) |
| icon | Component \| undefined | undefined | Lucide icon component for prefix |
| disabled | boolean | false | Disables input |

### Select
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| label | string \| undefined | undefined | Field label |
| options | SelectOption[] | required | Available options |
| value | string | '' | Selected value |
| placeholder | string | 'Select...' | Placeholder when empty |
| disabled | boolean | false | Disables select |

```typescript
interface SelectOption {
  value: string;
  label: string;
}
```

### Modal
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| open | boolean | false | Controls visibility |
| onClose | () => void | required | Close handler |
| title | string | '' | Modal title |
| children | Snippet | required | Modal body content |
| footer | Snippet \| undefined | undefined | Optional footer slot |

Uses bits-ui Dialog primitive for focus trap, Escape close, body scroll lock. Full-screen on viewports < 640px.

### MetricCard
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| label | string | required | Metric label |
| value | string \| number | required | Metric value |
| trend | Trend \| undefined | undefined | Trend direction |
| trendValue | string \| undefined | undefined | Trend text (e.g., "+12%") |
| highlight | boolean | false | Adds primary accent border |
| children | Snippet \| undefined | undefined | Optional extra content |

### PageHeader
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| title | string | required | Page title |
| description | string \| undefined | undefined | Subtitle/description |
| actions | Snippet \| undefined | undefined | Action buttons slot |

### EmptyState
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| icon | Component \| undefined | undefined | Lucide icon component |
| title | string | required | Empty state title |
| description | string \| undefined | undefined | Explanatory text |
| action | Snippet \| undefined | undefined | CTA button slot |

### LoadingSkeleton
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| variant | 'text' \| 'card' \| 'table-row' \| 'circle' | 'text' | Shape variant |
| lines | number | 3 | Number of text lines (for 'text' variant) |
| rows | number | 5 | Number of rows (for 'table-row' variant) |

### IconButton
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| icon | Component | required | Lucide icon component |
| label | string | required | Accessible aria-label |
| variant | 'ghost' \| 'secondary' | 'ghost' | Visual style |
| size | 'sm' \| 'md' | 'md' | Size preset |
| disabled | boolean | false | Disables interaction |

### Sidebar
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| items | SidebarItem[] | required | Navigation items |
| variant | 'default' \| 'admin' | 'default' | Shows admin badge when 'admin' |
| user | SidebarUser | required | Current user info |
| onLogout | () => void | required | Logout handler |

```typescript
interface SidebarItem {
  icon: Component;      // Lucide icon component
  label: string;
  href: string;
  badge?: string;       // Optional badge text
}

interface SidebarUser {
  email: string;
  role: string;
  displayName?: string;
}
```

## Entity Relationships

```
Design Tokens (app.css :root)
  └── consumed by → Tailwind Config (tailwind.config.ts theme.extend)
       └── consumed by → UI Components (token-mapped classes)
            └── consumed by → Page Routes (import components)

Sidebar Component
  ├── receives → SidebarItem[] (from layout)
  ├── receives → SidebarUser (from auth store)
  └── contains → Badge (role display), IconButton (logout)

Table Component
  ├── contains → LoadingSkeleton (loading state)
  ├── contains → EmptyState (no data state)
  └── receives → Badge (via row snippet for severity/status columns)
```
