---
name: pinia-store-conventions
description: This skill should be used when creating or modifying Pinia stores, structuring store state and actions, handling loading and error states, persisting data to localStorage, defining getters, or following the project's store patterns.
version: 1.0.0
---

# Pinia Store Conventions

## One Store Per Domain

One store per domain concern: `projects`, `videos`, `jobs`, `tts`, etc.

## Store Structure: state → getters → actions

Use the Setup Store (Composition API) syntax — consistent with `<script setup>`:

```js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as thingApi from '@/api/things'

export const useThingsStore = defineStore('things', () => {
  // --- State ---
  const things = ref([])
  const loading = ref(false)
  const error = ref(null)

  // --- Getters ---
  const totalCount = computed(() => things.value.length)
  const hasThings = computed(() => things.value.length > 0)

  // --- Actions ---
  async function fetchThings() {
    loading.value = true
    error.value = null          // always reset error at start
    try {
      const { data } = await thingApi.listThings()
      things.value = data
    } catch (err) {
      error.value = err.message || 'Failed to fetch things'
    } finally {
      loading.value = false     // always clear loading in finally
    }
  }

  async function createThing(payload) {
    loading.value = true
    error.value = null
    try {
      const { data } = await thingApi.createThing(payload)
      things.value.push(data)
      return data
    } catch (err) {
      error.value = err.message || 'Failed to create thing'
      throw err                 // re-throw if caller needs to know
    } finally {
      loading.value = false
    }
  }

  return { things, loading, error, totalCount, hasThings, fetchThings, createThing }
})
```

## Loading and Error State Rules

1. **Reset `error` at the start** of every action: `error.value = null`
2. **Set `loading = false` in `finally`** — never in try/catch branches
3. **Set `error` in the catch block** — always provide a fallback message
4. **Return data** from create/update actions so callers can use it

## localStorage Persistence

Persist user preferences within store actions, not in components:

```js
// In the store action
function setVoice(voiceId) {
  selectedVoice.value = voiceId
  localStorage.setItem('tts_selected_voice', voiceId)
}

function init() {
  const saved = localStorage.getItem('tts_selected_voice')
  if (saved) selectedVoice.value = saved
}
```

## File Location

`frontend/src/stores/<domain>.js` — one file per domain.
