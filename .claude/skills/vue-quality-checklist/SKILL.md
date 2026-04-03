---
name: vue-quality-checklist
description: This skill should be used when finishing a Vue frontend task, reviewing completed frontend code, or performing a pre-commit quality check on Vue components, stores, or composables.
version: 1.0.0
---

# Vue Frontend Quality Checklist

Run through this checklist before considering any frontend task complete.

## Tests
- [ ] All new code has corresponding tests that pass
- [ ] Tests cover: happy path, loading state, error state, user interactions
- [ ] No skipped or commented-out tests

## Vue Component Quality
- [ ] Uses `<script setup>` syntax (never Options API)
- [ ] All props defined with `defineProps` and explicit types
- [ ] All emitted events declared with `defineEmits`
- [ ] All `v-for` loops have stable `:key` bindings (not array index if list can reorder)
- [ ] Event listeners, WebSocket connections, and timers cleaned up in `onUnmounted`
- [ ] No `console.log` statements in production code

## Styling
- [ ] Uses `<style scoped lang="scss">`
- [ ] Class names follow BEM convention
- [ ] No inline styles in templates
- [ ] No hardcoded color values — uses CSS custom properties
- [ ] No `:deep()` selectors (prefer props/slots)

## Architecture
- [ ] API calls are in `api/` layer, not in components
- [ ] Store actions reset `error` at start and manage `loading` in `finally`
- [ ] localStorage reads/writes happen in stores, not components
- [ ] No hardcoded backend URLs — use `api/` layer and `utils/url.js`
- [ ] Interactive elements have `data-testid` attributes

## After Completing Any Task
- [ ] Run `npm run test` in `frontend/` — all tests pass
- [ ] Remind the user to rebuild: `docker compose up -d --build frontend`
