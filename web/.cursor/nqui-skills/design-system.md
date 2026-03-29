---
name: nqui-design-system
description: Design system conventions for nqui component library. Use when creating or modifying nqui UI components to ensure sizing, spacing, and styling consistency.
---

# nqui Design System

Guidelines for AI agents implementing or modifying nqui components. Follow these rules to maintain visual consistency.

## Control Size Scale

All interactive controls (buttons, toggles, inputs, selects) use a unified scale:

| Size     | Height | Min Width | Use Case                          |
|----------|--------|-----------|-----------------------------------|
| `sm`     | h-6 (24px) | min-w-6 | Compact UIs, dense tables, toolbars |
| `default`| h-7 (28px) | min-w-7 | Standard forms, primary actions       |
| `lg`     | h-8 (32px) | min-w-8 | Emphasis, secondary actions         |

### Semantic Rule

`size="sm"` on Button MUST produce the same height as `size="sm"` on ToggleGroupItem, SegmentedControlItem, SelectTrigger, etc. Never introduce component-specific scales.

## Layout Heights

| Element | Height | Use Case |
|---------|--------|----------|
| Header | h-12 (48px) | Page header, app bar, sticky nav |
| Sidebar header | h-12 (48px) | Sidebar section title bar |

Fits 4px/8px grid. Default button (h-7) in 48px header leaves 10px top/bottom; h-8 leaves 8px. Use px-4, gap-2 or gap-4 for horizontal spacing.

## Component Size Mapping

| Component | sm | default | lg |
|-----------|-----|---------|-----|
| Button | h-6 min-w-6 px-2 text-xs | h-7 min-w-7 px-3 | h-8 min-w-8 px-4 |
| Button (icon) | — | h-7 w-7 p-0 | — |
| Toggle | h-6 min-w-6 px-1.5 | h-7 min-w-7 px-2 | h-8 min-w-8 px-2 |
| ToggleGroupItem | (uses Toggle) | | |
| SelectTrigger | h-6 | h-7 | — |
| Input | — | h-7 px-3 py-1.5 text-sm | — |
| InputGroup | — | h-7 | — |

## Border Radius & Nested Radius

| Token | Formula | Use Case |
|-------|---------|----------|
| --radius-sm | calc(--radius - 4px) | Compact controls, kbd |
| --radius-md | calc(--radius - 2px) | Default (Button, Input, Card) |
| --radius-lg | var(--radius) | Large surfaces |
| --radius-xl | calc(--radius + 4px) | Modals, sheets |

**Nested radius formula:** `R_inner = R_outer - offset`. When a smaller element sits inside a larger one with padding, use concentric radius so corners align.

```
/* Inner card with p-3 (12px) inset inside radius-lg card */
border-radius: calc(var(--radius-lg) - var(--spacing-3));
```

- **Standalone** components (Button, Input) use radius tokens directly.
- **Nested** elements (Card inside Card, panel in modal) use `calc(outer - offset)`.
- Clamp to avoid negatives: `max(0px, calc(...))` when offset ≥ outer.

## Typography

| Size | Class | Use Case |
|------|-------|----------|
| sm | `text-xs` or `text-[0.625rem]` | Compact controls, labels |
| default | `text-sm` | Body, inputs, buttons |
| base | `text-base` | Section titles, headings |

Font: `--font-sans` (Inter Variable). Leading: `leading-normal` or `text-xs/relaxed`.

## When Adding a New Component

1. **Use the scale** – If the component has a `size` prop, map `sm`→h-6, `default`→h-7, `lg`→h-8.
2. **Match padding** – Text controls: px-2–3, py-1.5. Icon-only: p-0 with explicit size.
3. **Text size** – sm: `text-xs` or `text-[0.625rem]`, default: `text-sm`, lg: `text-sm`.
4. **Border radius** – Use `rounded-md` (default) or `rounded-[min(var(--radius-md),8px)]` for sm; **Button** uses full pill (`rounded-full`). For nested layouts, use `calc(outer - offset)`.

## Grouped Controls (ButtonGroup, ToggleGroup)

- **Shared border** – Container: `rounded-full border border-input overflow-hidden` (pill outer edge)
- **Child borders** – Items: `border-0` (container provides the border)
- **Dividers** – ToggleGroup: item borders (`border-foreground/20`) between items. Or `ToggleGroupSeparator` when `separator={false}`.
- **Corners** – First item: rounded-l (or rounded-t vertical), last: rounded-r (or rounded-b)
- **Several groups on one horizontal row** – `ButtonGroup`’s container is **`inline-flex`**, so multiple sibling groups in normal flow behave like **inline boxes** and align to **baseline**. Mixed content (labels vs icons vs `ButtonGroupText`) then produces inconsistent vertical alignment. Prefer an explicit row container: **`flex flex-wrap items-center gap-*`**, or **grid** columns—so you choose **cross-axis alignment** (`items-center`, `items-end`, etc.) instead of inheriting baseline alignment from inline layout.

## Toggle & ToggleGroup Visual Treatment (Visibility on Any Background)

Toggles and ToggleGroup items must remain visible on card, sidebar, and varied backgrounds:

| State | Default/Outline | Segmented (single select) |
|-------|-----------------|---------------------------|
| **Off** | `border border-input/60` (or `border-input`), `shadow-sm`, `bg-background/50` (or transparent) | Transparent |
| **On** | `bg-secondary` + `nqui-button-gradient` + `nqui-button-shadow` (secondary-like layering) | `bg-primary` + gradient + shadow |
| **Active (pressed)** | `active:shadow-[inset_0_3px_5px_rgba(0,0,0,0.125)]` | Same |

Never use flat `bg-muted` only for selected state; always add gradient + shadow for depth and visibility.

## Toolbar & In-Context Design

**Rule:** Show controls in realistic app context, not isolated. Reference: `packages/nqui/src/pages/ComponentShowcase.tsx` (Toggle & ToggleGroup section).

| Context | Layout | Example |
|---------|--------|---------|
| Document editor | Toolbar above content area, `bg-muted/30` container, `Separator` between control groups | Bold/Italic/Underline \| Align Left/Center/Right |
| Chart/settings panel | Label + inline controls, `rounded-lg border bg-muted/30 p-3` | Y-axis: Linear/Log; Size: S/M/L |
| Standalone | Inline with related UI, not floating alone | Pin, Mute, single Toggle |

## Bounded content (default UX)

- **Rule:** Interactive surfaces should not **visually bleed** outside their box: prefer **ellipsis** (`truncate`), **line-clamp**, **controlled scroll**, or **wrapping** (`break-words` / `whitespace-normal`) instead of letting text or icons paint past padding in narrow layouts.
- **Not universal:** Portals (dropdowns, popovers), **tooltips**, and **drag overlays** intentionally escape bounds. **Data tables** may use horizontal scroll. Choose per component.
- **Flex gotcha:** `inline-flex` + icon + `whitespace-nowrap` + raw **string** children keeps an implicit **min-width: min-content**; parents need **`min-w-0`** (and often **`max-w-full`**) on the control and a truncating inner wrapper for long labels.
- **Built-in helpers in nqui:** Shared `wrapInlineLabelTextNodes` + `min-w-0 max-w-full` on **Button**, **Toggle**, **TabsTrigger**, **Badge**, **ComboboxChip**; **SelectTrigger** uses **`min-w-0 max-w-full`** and **`min-w-0`** on the value slot with **`line-clamp-1`**. **Carousel** prev/next sit **inside** the carousel box so they don’t spill out of **Card** (override via `className` if you want outside arrows).
- **Card:** **Card** uses **`min-w-0`** on shell + header/content/footer for flex/grid safety but keeps **`overflow-visible`** so overlays aren’t clipped; don’t rely on **`overflow-hidden`** on Card as a global “catch-all” unless you accept clipping dropdowns/focus.

## Customization

- End users override via `className` or `size` when supported.
- Do NOT hardcode heights in consumer code when the component supports `size`.
- Prefer semantic sizes over pixel values in component defaults.

## Hit area utilities

**Hit area** expands the pointer target; it does **not** replace control **size** (sm / default / lg). Use **opt-in** on **Checkbox** / **Switch** for padded rows or cells—not as a global default. Avoid large overlapping hit areas in dense toolbars. See **`SKILL.md`** (Hit area) in this folder and `packages/nqui/docs/components/nqui-checkbox.md` / `nqui-switch.md`.

## Files to Check for Consistency

- `packages/nqui/src/components/ui/button.tsx`
- `packages/nqui/src/components/ui/toggle.tsx`
- `packages/nqui/src/components/ui/toggle-group.tsx`
- `packages/nqui/src/components/ui/input.tsx`
- `packages/nqui/src/components/ui/select.tsx`
- `packages/nqui/src/components/ui/combobox.tsx`

## Anti-Patterns

- **Different heights for same size** – Button h-10 while Toggle h-7 = inconsistent.
- **Component-specific scales** – Do not add `xs` or `xl` without updating the design system doc.
- **Overriding in showcase** – If showcase needs `className="h-9"` to look right, the component default is wrong.
