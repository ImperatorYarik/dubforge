---
name: vue-router-conventions
description: This skill should be used when adding routes to Vue Router, configuring navigation guards, using router-link or programmatic navigation, lazy-loading view components, or setting up route params and meta fields.
version: 1.0.0
---

# Vue Router Conventions

## Route Configuration

All routes live in `frontend/src/router/index.js`.

```js
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'projects',                                        // always define name
    component: () => import('@/views/ProjectsView.vue'),     // always lazy-load
    meta: { requiresAuth: false }
  },
  {
    path: '/projects/:projectId',
    name: 'project-detail',
    component: () => import('@/views/ProjectDetailView.vue'),
    props: true   // pass route params as props when possible
  }
]
```

## Named Routes — Always Use Names

Never use path strings in navigation — use named routes:

```js
// Good — named route
router.push({ name: 'project-detail', params: { projectId: id } })
<router-link :to="{ name: 'projects' }">Back</router-link>

// Bad — hardcoded path string
router.push('/projects/123')
```

## Lazy Loading — Always

Always lazy-load view components. This splits them into separate chunks and improves initial load:

```js
// Good
component: () => import('@/views/ProjectDetailView.vue')

// Bad — eager import
import ProjectDetailView from '@/views/ProjectDetailView.vue'
component: ProjectDetailView
```

## Navigation Guards

Use navigation guards for auth checks and data prefetching:

```js
// Per-route guard
{
  path: '/settings',
  name: 'settings',
  component: () => import('@/views/SettingsView.vue'),
  beforeEnter: (to, from) => {
    if (!isAuthenticated()) return { name: 'login' }
  }
}

// Global guard (in router/index.js)
router.beforeEach((to, from) => {
  if (to.meta.requiresAuth && !isAuthenticated()) {
    return { name: 'login' }
  }
})
```

## Route Params as Props

Use `props: true` to pass route params directly as component props — keeps components decoupled from the router:

```js
// Router
{ path: '/projects/:projectId', name: 'project-detail', props: true }

// Component
const props = defineProps({ projectId: { type: String, required: true } })
```
