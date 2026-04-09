---
name: vue-api-layer
description: This skill should be used when adding API calls, creating new API client files, deciding where HTTP requests belong, naming API functions, or structuring the frontend api/ layer for this project.
version: 1.0.0
---

# Vue API Layer Conventions

## Rule: All HTTP Calls Live in `api/`

Never make axios calls directly in components or stores. All HTTP requests belong in `frontend/src/api/`.

```
frontend/src/api/
  client.js       # axios instance with base URL + interceptors
  projects.js     # /projects endpoints
  videos.js       # /videos endpoints
  jobs.js         # /jobs endpoints
  tts.js          # /tts endpoints
```

## One File Per Backend Resource

Match the API file to the FastAPI router groupings. Each file handles one REST resource.

## Export Named Functions

```js
// api/projects.js
import client from './client'

export function listProjects() {
  return client.get('/projects/')
}

export function getProject(projectId) {
  return client.get(`/projects/${projectId}`)
}

export function createProject(data) {
  return client.post('/projects/', data)
}

export function deleteProject(projectId) {
  return client.delete(`/projects/${projectId}`)
}
```

## Function Naming Convention

| Operation | Naming |
|---|---|
| List all | `listThings()` |
| Get one | `getThing(id)` |
| Create | `createThing(data)` |
| Update | `updateThing(id, data)` |
| Delete | `deleteThing(id)` |
| Custom action | `dubVideo(projectId, videoId, opts)` |

## Return the Promise

Always return the axios promise — let the **store** handle errors, not the API function:

```js
// Good — return the promise
export function listVideos(projectId) {
  return client.get(`/projects/${projectId}/videos/`)
}

// Bad — swallowing errors in the API layer
export async function listVideos(projectId) {
  try {
    return await client.get(`/projects/${projectId}/videos/`)
  } catch (err) {
    console.error(err)  // don't do this
  }
}
```

## No Hardcoded URLs

Never hardcode backend URLs in components or stores. Use the `api/` layer and `utils/url.js` utilities:

```js
// Good
import { getVideoStreamUrl } from '@/utils/url'

// Bad
const url = `http://localhost:8000/videos/${id}/stream`
```
