---
name: vue3-composition-api
description: This skill should be used when writing or reviewing Vue 3 component logic, choosing between ref and reactive, using computed properties, watching state, handling lifecycle hooks, defining props and emits, or applying Composition API patterns with script setup syntax.
version: 1.0.0
---

# Vue 3 Composition API Patterns

## Script Setup

Always use `<script setup>` — never Options API.

```vue
<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
</script>
```

## Reactivity Primitives

- `ref` for primitives: `const count = ref(0)` → access via `count.value`
- `reactive` for plain objects: `const state = reactive({ name: '', age: 0 })`
- Never use `reactive` for primitives — it doesn't work
- Prefer `ref` when unsure — more explicit, works everywhere

## Computed Properties

Use `computed` for any derived state — never compute in templates:

```js
// Good
const fullName = computed(() => `${firstName.value} ${lastName.value}`)

// Bad — logic in template
// {{ firstName + ' ' + lastName }}
```

## Watchers

Prefer `computed` over `watch` whenever possible. Use `watch` for side effects:

```js
// Watch a ref
watch(someRef, (newVal, oldVal) => { /* side effect */ })

// Watch multiple sources
watch([refA, refB], ([a, b]) => { /* ... */ })

// Immediate + deep
watch(obj, handler, { immediate: true, deep: true })

// watchEffect for automatic dependency tracking
watchEffect(() => { console.log(someRef.value) })
```

## Lifecycle Hooks

```js
onMounted(() => {
  // DOM available, start fetching data, set up subscriptions
})

onUnmounted(() => {
  // ALWAYS clean up: clear timers, close WebSockets, remove event listeners
  clearInterval(intervalId)
  socket.close()
  window.removeEventListener('resize', handler)
})
```

## Props and Emits

```js
// Props with types and defaults
const props = defineProps({
  title: { type: String, required: true },
  count: { type: Number, default: 0 },
  items: { type: Array, default: () => [] }
})

// Emits declaration (kebab-case event names)
const emit = defineEmits(['update:modelValue', 'submit', 'item-selected'])

// Usage
emit('item-selected', { id: 123 })
```

## Template Best Practices

- `v-for` always needs a stable, unique `:key` — never use index if list can reorder
- `v-if` for infrequently toggled content (removes from DOM)
- `v-show` for frequently toggled content (CSS display toggle)
- Keep templates declarative — move logic into `<script setup>` or composables