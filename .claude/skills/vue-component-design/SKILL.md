---
name: vue-component-design
description: This skill should be used when designing Vue components, deciding between presentational and container components, structuring component props and emits, using slots, applying scoped styles, adding data-testid attributes, or splitting large components.
version: 1.0.0
---

# Vue Component Design Principles

## Single Responsibility

Each component does one thing well. If a component exceeds ~200 lines, consider splitting it.

## Presentational vs Container Components

**Presentational (dumb) components:**
- Receive data via props only
- Communicate back via emits only
- No store access, no direct API calls
- Highly reusable and testable

**Container (smart) components:**
- Connect to Pinia stores
- Orchestrate data fetching
- Pass data down to presentational children

```vue
<!-- Presentational: VideoCard.vue -->
<script setup>
defineProps({ video: { type: Object, required: true } })
defineEmits(['select', 'delete'])
</script>

<!-- Container: VideosView.vue -->
<script setup>
import { useVideosStore } from '@/stores/videos'
const store = useVideosStore()
onMounted(() => store.fetchVideos())
</script>
```

## Testability: data-testid Attributes

Add `data-testid` to **all interactive elements** and key display elements:

```vue
<button data-testid="submit-btn" @click="submit">Submit</button>
<input data-testid="title-input" v-model="title" />
<div data-testid="error-message" v-if="error">{{ error }}</div>
```

## Slots for Composability

Use default and named slots to make components flexible:

```vue
<!-- Component definition -->
<template>
  <div class="card">
    <header v-if="$slots.header" class="card__header">
      <slot name="header" />
    </header>
    <div class="card__body">
      <slot />
    </div>
    <footer v-if="$slots.footer" class="card__footer">
      <slot name="footer" />
    </footer>
  </div>
</template>

<!-- Usage -->
<AppCard>
  <template #header>Card Title</template>
  Main content goes here
</AppCard>
```

## Scoped Styles

Always use `<style scoped>` to prevent style leakage:

```vue
<style scoped lang="scss">
.component-name {
  /* styles only apply to this component */
}
</style>
```

Avoid `:deep()` selectors — prefer props or slots for customization instead.
