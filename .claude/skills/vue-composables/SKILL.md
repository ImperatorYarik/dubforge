---
name: vue-composables
description: This skill should be used when creating Vue composables, extracting reusable stateful logic, naming composables, handling cleanup in composables, or deciding when to use a composable vs a store vs inline component logic.
version: 1.0.0
---

# Vue Composables

## When to Use a Composable

Use a composable when:
- The same stateful logic appears in 2+ components
- The logic involves reactive state + lifecycle management
- The logic is complex enough to warrant isolation (e.g., WebSocket connection, debounced input)

Use a **store** instead when state needs to be shared across distant components or persisted.
Use **inline component logic** when it's simple and only used in one place.

## Naming and Location

- File: `frontend/src/composables/use<Name>.js` (camelCase, `use` prefix)
- Name: `useToast`, `useWebSocket`, `useDebounce`, `useClipboard`

## Structure

```js
import { ref, onMounted, onUnmounted } from 'vue'

export function useWindowSize() {
  const width = ref(window.innerWidth)
  const height = ref(window.innerHeight)

  function update() {
    width.value = window.innerWidth
    height.value = window.innerHeight
  }

  onMounted(() => window.addEventListener('resize', update))
  onUnmounted(() => window.removeEventListener('resize', update))  // REQUIRED cleanup

  return { width, height }  // always return reactive refs/computed, not raw values
}
```

## Rules

1. **Always return reactive refs or computed** — never raw values (caller can't watch raw values)
2. **Clean up ALL side effects** in `onUnmounted`: timers, WebSocket connections, event listeners, subscriptions
3. **Accept options as a single object** for flexibility:
   ```js
   export function useDebounce(value, options = { delay: 300 }) { ... }
   ```
4. **Keep composables pure** — no store access unless the composable specifically bridges a store

## Existing Composable in This Project

- `useToast.js` — Toast notification composable. Use this for showing success/error/info toasts rather than rolling a new notification system.
