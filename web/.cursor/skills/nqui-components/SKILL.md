---
name: nqui-components
description: Component implementation for nqui. Use when building UI with @nqlib/nqui, choosing components, or implementing a specific component. Always read from docs path before implementing.
---

# nqui Components

**When to load:** User asks about nqui components, which component to use, how to implement X, or builds UI with nqui.

**Action:** Read from the docs path before implementing. Do not guess – the docs have exact import, props, and examples.

## Documentation path (always use this)

```
node_modules/@nqlib/nqui/docs/components/
```

## File resolution

| User asks | File to read |
|-----------|--------------|
| Component index, use cases, which component for X | `node_modules/@nqlib/nqui/docs/components/README.md` |
| How to use Button | `node_modules/@nqlib/nqui/docs/components/nqui-button.md` |
| How to use ToggleGroup | `node_modules/@nqlib/nqui/docs/components/nqui-toggle-group.md` |
| Any component X | `node_modules/@nqlib/nqui/docs/components/nqui-<kebab-name>.md` (e.g. nqui-data-table.md) |

**Rule:** For any component question, read the doc first. The docs have import, variants, props, and examples.

## Quick rules (details in README.md)

- **Toolbar/inline selection** → ToggleGroup (never RadioGroup)
- **Form context** → RadioGroup, Checkbox
- **Actions** → Button, ButtonGroup
- **Context-first:** Place controls in realistic layout (toolbar, chart settings), not floating alone

## Import

```tsx
import { Button, ToggleGroup, ToggleGroupItem } from "@nqlib/nqui"
```

CSS: `@import "@nqlib/nqui/styles"` in main CSS (run `npx @nqlib/nqui init-css` first).
