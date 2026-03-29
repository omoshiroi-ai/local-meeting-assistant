---
name: nqui Components
description: Component implementation guide for nqui. Use when building UI, designing app layouts, or implementing components with @nqlib/nqui.
---

# nqui Components Guide

Reference `packages/nqui/docs/components/README.md` for the full component index and implementation rules.

## Quick Reference

1. **Main index:** `packages/nqui/docs/components/README.md` - all components, use cases, prerequisites
2. **Per-component:** `packages/nqui/docs/components/nqui-<name>.md` - import, examples, variants
3. **Design system:** this folder - sizing, grouped controls

## App Design Rule: Inline Selection → ToggleGroup

When designing app UI (toolbars, headers, inline controls):

| Context | Use | NOT |
|---------|-----|-----|
| View mode (List/Grid/Table), scale (Linear/Log), size (S/M/L) | **ToggleGroup** `type="single"` | RadioGroup |
| Format toolbar (Bold/Italic/Underline), multi-toggle | **ToggleGroup** `type="multiple"` | Multiple Checkboxes |
| Toolbar actions (Undo/Redo, align) | **ButtonGroup** | - |
| Single on/off (Bold, Mute) | **Toggle** | - |

**Rule:** Inline/toolbar selection = ToggleGroup. Use RadioGroup only for form context (settings page, modal form, stacked list).

## App Design Rule: Context-First (Toolbar in Real Environment)

**Rule:** Never show Toggle/ToggleGroup/ButtonGroup in isolation. Always place them in realistic app context.

| Context | Layout | Reference |
|---------|--------|-----------|
| Document editor | Toolbar above content; `bg-muted/30` container; `Separator` between groups | ComponentShowcase → Toggle & ToggleGroup |
| Chart/settings | Label + inline controls; `rounded-lg border bg-muted/30 p-3` | ComponentShowcase → Chart settings |
| Standalone | Inline with related UI | ComponentShowcase → Standalone toggle |

**Canonical implementation:** `packages/nqui/src/pages/ComponentShowcase.tsx` — Toggle & ToggleGroup section.

## Design System Conventions

See **`design-system.md`** in this folder for sizing, grouped controls (including pill **ButtonGroup** / **ToggleGroup** shells), and file paths under `packages/nqui/src/components/ui/`.

### Control Sizing
- sm = h-6
- default = h-7
- lg = h-8

### Z-Index
Always use CSS variables from elevation.css:
- `--z-content` (10) - standard content
- `--z-sticky-content` (15) - sticky within containers
- `--z-sticky-page` (20) - page-level sticky
- `--z-floating` (30) - floating panels
- `--z-modal-backdrop` (40)
- `--z-modal` (50)
- `--z-popover` (60)
- `--z-tooltip` (70)

### FrostedGlass (sticky glass headers)

`FrostedGlass` is only the blur layer. Implementations need a **second row** with `bg-background/40`, `relative z-[var(--z-content)]`, and content that **scrolls behind** the sticky header. Full checklist, props, and troubleshooting: **`packages/nqui/docs/components/nqui-frosted-glass.md`**. Canonical page header: `AppLayout`; card: **Card** `stickyHeader`.

### Component Naming
- Default exports are the enhanced/polished variants; use **Core\*** for plain primitives
- Implementations are consolidated under **`ui/`** (not separate `custom/enhanced-*` per component for Button, Badge, Checkbox, Select, Combobox, Sonner)
- File names: kebab-case
- Component names: PascalCase

### Hit area (optional)

Library CSS includes [Bazza hit-area](https://bazza.dev/craft/2026/hit-area) utilities. For **Checkbox** / **Switch** in padded tables or lists, pass **`className="hit-area-6"`** (or `hit-area-4`, axis variants) on the **component root**, not on a wrapper-only parent. Opt-in only; use **`hit-area-debug`** while tuning. Details: `packages/nqui/docs/components/nqui-checkbox.md`, `nqui-switch.md`; examples: `ComponentShowcase` Checkbox + Switch sections.

## Key Dependencies

Required peer dependencies:
- `@hugeicons/react`
- `@hugeicons/core-free-icons`

Optional:
- `next-themes` - for theme toggle
- `tw-animate-css` - for animations

## Installation & Setup

```bash
# Quick setup
npx @nqlib/nqui init-css

# App setup with sidebar
npx @nqlib/nqui init-css --sidebar

# Install peer dependencies
npx @nqlib/nqui install-peers
```

## CSS Variables

All components use CSS variables. Key ones:
- `--background`, `--foreground`
- `--muted`, `--muted-foreground`
- `--accent`, `--accent-foreground`
- `--border`, `--ring`
- `--primary`, `--primary-foreground`
- `--destructive`, `--destructive-foreground`
