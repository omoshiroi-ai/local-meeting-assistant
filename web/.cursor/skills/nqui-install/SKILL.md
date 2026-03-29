---
name: nqui-install
description: Install and setup nqui. Use when user wants to install nqui, set up project, fix missing peers, or run setup commands. Execute these commands in the project root.
---

# nqui Install & Setup

**When to load:** User asks to install nqui, set up a new project, fix "module not found" or missing peer deps, or run setup.

**Action:** Execute the relevant command(s) below in the project root. Run in sequence when doing full setup.

## 1. Install nqui + peers

**Minimal (icons only):**
```bash
pnpm add @nqlib/nqui @hugeicons/react @hugeicons/core-free-icons
```
(npm: `npm install @nqlib/nqui @hugeicons/react @hugeicons/core-free-icons`)

**Full (all optional components):**
```bash
npx @nqlib/nqui install-peers
```
Or manually:
```bash
pnpm add @nqlib/nqui @hugeicons/react @hugeicons/core-free-icons cmdk @dnd-kit/core @dnd-kit/modifiers @dnd-kit/sortable @dnd-kit/utilities embla-carousel-react @tanstack/react-table react-day-picker date-fns sonner vaul react-resizable-panels @base-ui/react
```
(npm: `npm install @nqlib/nqui @hugeicons/react @hugeicons/core-free-icons cmdk @dnd-kit/core @dnd-kit/modifiers @dnd-kit/sortable @dnd-kit/utilities embla-carousel-react @tanstack/react-table react-day-picker date-fns sonner vaul react-resizable-panels @base-ui/react`)

## 2. Setup CSS (required)

```bash
npx @nqlib/nqui init-css
```

Then add to main CSS (app/globals.css or src/index.css): `@import "@nqlib/nqui/styles";`
Or copy contents of `nqui/nqui-setup.css` to top of main CSS.

## 3. Refresh Cursor rules (optional)

```bash
npx @nqlib/nqui init-cursor
```

## File locations

- Docs: `node_modules/@nqlib/nqui/docs/components/README.md` (index) and `node_modules/@nqlib/nqui/docs/components/nqui-<name>.md` (per component)
- Check setup: `npx nqui-setup`
