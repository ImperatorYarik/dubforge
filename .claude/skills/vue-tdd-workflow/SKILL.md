---
name: vue-tdd-workflow
description: This skill should be used when writing frontend tests, following the TDD cycle for Vue components or stores, setting up Vitest tests, mocking API modules, testing Pinia stores, testing Vue components with Vue Test Utils, or running frontend tests.
version: 1.0.0
---

# Vue TDD Workflow

## The TDD Cycle (MANDATORY)

1. **RED** — Write a failing test that describes the desired behaviour. Run it and confirm it fails with a meaningful error (not a syntax error).
2. **GREEN** — Write the minimum production code to pass the test. No extra logic.
3. **REFACTOR** — Clean up, keep tests green. Extract helpers, clean names, remove duplication.

Never write production code without a failing test first.

## Test File Naming and Location

All tests go in `frontend/src/__tests__/`:

| What | File pattern |
|---|---|
| Pinia store | `__tests__/stores.<name>.test.js` |
| Composable | `__tests__/<composableName>.test.js` |
| Component | `__tests__/components/<ComponentName>.test.js` |
| Utility | `__tests__/<fileName>.test.js` |

## Store Test Template

```js
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/things', () => ({
  listThings: vi.fn(),
  createThing: vi.fn(),
}))

import * as thingsApi from '@/api/things'
import { useThingsStore } from '@/stores/things'

describe('useThingsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('initialises with empty list', () => {
    const store = useThingsStore()
    expect(store.things).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  describe('fetchThings', () => {
    it('sets things on success', async () => {
      thingsApi.listThings.mockResolvedValue({ data: [{ id: '1' }] })
      const store = useThingsStore()
      await store.fetchThings()
      expect(store.things).toEqual([{ id: '1' }])
      expect(store.loading).toBe(false)
    })

    it('sets error on failure', async () => {
      thingsApi.listThings.mockRejectedValue(new Error('Network error'))
      const store = useThingsStore()
      await store.fetchThings()
      expect(store.error).toBeTruthy()
      expect(store.loading).toBe(false)
    })

    it('sets loading true during fetch', async () => {
      let resolvePromise
      thingsApi.listThings.mockReturnValue(new Promise(r => resolvePromise = r))
      const store = useThingsStore()
      const promise = store.fetchThings()
      expect(store.loading).toBe(true)
      resolvePromise({ data: [] })
      await promise
      expect(store.loading).toBe(false)
    })
  })
})
```

## Component Test Template

```js
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MyComponent from '../components/MyComponent.vue'

describe('MyComponent', () => {
  it('renders expected content', () => {
    const wrapper = mount(MyComponent, {
      props: { title: 'Test Title' }
    })
    expect(wrapper.text()).toContain('Test Title')
  })

  it('shows error message when error prop set', async () => {
    const wrapper = mount(MyComponent, { props: { error: 'Something failed' } })
    expect(wrapper.find('[data-testid="error-message"]').exists()).toBe(true)
  })

  it('emits close when button clicked', async () => {
    const wrapper = mount(MyComponent)
    await wrapper.find('[data-testid="close-btn"]').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
```

## Mocking Rules

- Mock API modules at the file top: `vi.mock('@/api/<name>', () => ({ fn: vi.fn() }))`
- Import the mock **after** `vi.mock` so the reference is to the mocked version
- Reset between tests: `vi.clearAllMocks()` in `beforeEach`
- For store tests: `setActivePinia(createPinia())` in `beforeEach`
- Use `mockResolvedValue` for success, `mockRejectedValue` for errors

## What to Cover

**Per store action:** initial state, loading state, success path (state updated + API called correctly), error path (error set, loading cleared)

**Per component:** renders expected elements, conditional rendering switches on state change, user interactions trigger correct emits/store calls, props validation

## Running Frontend Tests

```bash
cd frontend
npm run test                             # run once
npm run test -- --watch                  # watch mode (during RED phase)
npm run test -- --reporter=verbose       # verbose per-test output
npm run test -- --coverage               # coverage report
```
