---
name: Frontend Design System — Flat Light Minimalist
description: The frontend was redesigned from a dark cinema theme to a flat light minimalist theme. All design tokens now live in _tokens.scss with CSS custom properties.
type: project
---

The frontend design system was fully redesigned. Key facts:

- Canvas background: `#F8F9FA` (very light grey), surfaces: `#FFFFFF`
- Borders: `1px solid #EAEAEA` — NO box-shadows, NO drop-shadows, NO gradients
- Primary action: pure black `#000000` buttons with white text
- Text: primary `#202124`, secondary `#5F6368`
- Border radius: `4px` (--radius), `6px` (--radius-md)
- Font: system font stack `--font-body` (no custom fonts), `--font-mono` for code

**Design tokens** are in `/frontend/src/assets/scss/base/_tokens.scss` as CSS custom properties with `--color-*` prefix. Legacy aliases (`--bg`, `--amber`, `--teal`, etc.) are kept for backward compat with DubbingStudioView and other components that haven't been redesigned.

**Views redesigned with BEM class naming:**
- `ProjectsView.vue` — block: `.projects-view`
- `ProjectDetailView.vue` — block: `.detail-view`
- `TextToSpeechView.vue` — block: `.tts-view`
- `VoicesView.vue` — block: `.voices-view`

**Tests added** in `frontend/src/__tests__/views/` for all four views. All tests use `data-testid` attributes.

**Why:** User requested complete UX/UI redesign to a flat, 2D, minimalist aesthetic. Prior design was a dark "cinema control room" look.

**How to apply:** When adding new views or components, follow the flat light design: white surfaces, `#EAEAEA` borders, black action buttons, NO shadows. Use `--color-*` variables (not legacy `--amber`, `--teal`).
