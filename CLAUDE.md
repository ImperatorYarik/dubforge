# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

A microservice web application that dubs/translates videos to English using AI. The pipeline: downloads video → separates vocals (Demucs) → transcribes/translates (faster-whisper Whisper large-v3) → synthesizes dubbed audio (XTTS v2 zero-shot voice cloning) → time-stretches TTS to match original timing → ducks background audio during speech → muxes back into video. Also supports standalone transcription and text-to-speech generation.

## Running the Stack

```bash
# Start all services
docker compose up --build

# Start without GPU (no worker)
docker compose up frontend api mongodb redis minio
```

Required `.env` variables (see docker-compose.yaml for full list):
```
MONGO_URI=mongodb://mongodb:27017
S3_ENDPOINT=http://minio:9000
S3_PUBLIC_ENDPOINT=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
JWT_SECRET_KEY=<secret>
REDIS_URL=redis://redis:6379/0
HF_TOKEN=<huggingface token>   # optional, speeds up model downloads
COQUI_TOS_AGREED=1             # required for XTTS v2 on worker
```

Service ports: Frontend `5173`, API `8000`, MinIO `9000/9001`, MongoDB `27017`, Redis `6379`.

## Test-Driven Development

**All new features and bug fixes MUST follow TDD.** Write the test first, watch it fail, then write the minimum code to make it pass, then refactor.

### The Cycle

```
1. RED   — write a failing test that describes the desired behaviour
2. GREEN — write the minimum production code to make the test pass
3. REFACTOR — clean up, keep tests green
```

Never write production code without a failing test first. Never skip the refactor step.

---

### API Tests (pytest + FastAPI TestClient)

**Test location:** `api/tests/test_<module>.py`

**Naming convention:**
- File: `test_routers_<name>.py`, `test_crud_<name>.py`, `test_<util>.py`
- Class: group by endpoint or unit — `class TestCreateProject:`, `class TestListVideos:`
- Method: `test_<scenario>` — `test_success`, `test_returns_404_when_not_found`, `test_raises_on_db_error`

**Fixtures:** Use `conftest.py` for shared fixtures. The project-wide `client` fixture uses `fastapi.testclient.TestClient`.

**Mocking rules:**
- Mock at the **router boundary** — patch the dependency the router calls directly (e.g., `app.routers.projects.projects_repo`), not the underlying Motor call.
- Use `unittest.mock.AsyncMock` for coroutines, `MagicMock` for sync callables.
- Use `patch` as a context manager with `with (...):` grouping for multiple patches.
- Never mock `TestClient` itself — it uses the real FastAPI app.

**What to cover per router endpoint:**
1. Happy path — correct status code and response shape
2. Side effects — verify mocked dependencies were called with right args
3. Error paths — 404 when resource missing, 400/422 on bad input, 500 on service failure

**Template:**
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


MOCK_THING = {"id": "abc", "name": "test"}


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


class TestCreateThing:
    def test_success(self, client):
        with patch("app.routers.things.repo") as mock_repo:
            mock_repo.create = AsyncMock(return_value="abc")
            response = client.post("/things/", json={"name": "test"})
        assert response.status_code == 200
        assert response.json()["id"] == "abc"

    def test_returns_422_on_missing_field(self, client):
        response = client.post("/things/", json={})
        assert response.status_code == 422

    def test_calls_repo_with_correct_args(self, client):
        with patch("app.routers.things.repo") as mock_repo:
            mock_repo.create = AsyncMock(return_value="abc")
            client.post("/things/", json={"name": "test"})
        mock_repo.create.assert_called_once()
        call_args = mock_repo.create.call_args[0][0]
        assert call_args["name"] == "test"
```

**Running API tests:**
```bash
cd api
pip install -r requirements.txt
pytest                                   # all tests
pytest tests/test_routers_projects.py    # single file
pytest -k "test_name"                    # single test
pytest -x                                # stop on first failure (use during red phase)
pytest --tb=short                        # brief tracebacks
```

---

### Frontend Tests (Vitest + Vue Test Utils)

**Test location:** `frontend/src/__tests__/<subject>.test.js`

**Naming convention:**
- Stores: `stores.<name>.test.js`
- Composables: `<composableName>.test.js`
- Utilities: `<fileName>.test.js`
- Components: `components/<ComponentName>.test.js`

**Setup pattern:**
```js
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'   // for store tests
import { mount } from '@vue/test-utils'                // for component tests
```

**Mocking rules:**
- Mock API modules with `vi.mock('@/api/<name>', () => ({ fn: vi.fn() }))` at the top of the file.
- Import the mock AFTER `vi.mock` so the reference is to the mocked version.
- Reset between tests with `vi.clearAllMocks()` in `beforeEach`.
- For store tests, always call `setActivePinia(createPinia())` in `beforeEach`.
- Mock `localStorage` via `localStorage.clear()` + direct `setItem` calls — jsdom provides it.

**What to cover per store action:**
1. Initial state — correct defaults
2. Loading state — `loading` set to `true` during async, `false` after
3. Success path — state updated correctly, API called with right args
4. Error path — `error` state set, loading cleared
5. Side effects — localStorage reads/writes, router calls

**What to cover per component:**
1. Renders expected elements in default state
2. Conditional rendering (`v-if`) switches on prop/state change
3. User interactions (`await wrapper.find('button').trigger('click')`)
4. Emitted events — `wrapper.emitted('event-name')`
5. Props validation — renders correctly with various prop combinations

**Store template:**
```js
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useThingsStore } from '../stores/things'

vi.mock('@/api/things', () => ({
  listThings: vi.fn(),
  createThing: vi.fn(),
}))

import * as thingsApi from '@/api/things'

describe('useThingsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('initialises with empty list', () => {
    const store = useThingsStore()
    expect(store.things).toEqual([])
    expect(store.loading).toBe(false)
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
      thingsApi.listThings.mockRejectedValue(new Error('fail'))
      const store = useThingsStore()
      await store.fetchThings()
      expect(store.error).toBeTruthy()
      expect(store.loading).toBe(false)
    })
  })
})
```

**Component template:**
```js
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MyComponent from '../components/MyComponent.vue'

describe('MyComponent', () => {
  it('renders slot content', () => {
    const wrapper = mount(MyComponent, { slots: { default: 'Hello' } })
    expect(wrapper.text()).toContain('Hello')
  })

  it('emits close when button clicked', async () => {
    const wrapper = mount(MyComponent)
    await wrapper.find('[data-testid="close-btn"]').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
```

**Running frontend tests:**
```bash
cd frontend
npm run test          # run once
npm run test -- --watch        # watch mode (during development)
npm run test -- --reporter=verbose   # verbose per-test output
```

---

### TDD Workflow for a New Feature

Follow this order **without skipping steps**:

1. **Understand the requirement** — what is the API contract / component behaviour?
2. **Write the test file** (or add to existing file) with a failing test.
   - Run it: confirm it fails with a meaningful error (not a syntax error).
3. **Write the minimum production code** to pass the test.
   - No extra logic — only what the test requires.
4. **Run all tests** to confirm no regressions.
5. **Write the next failing test** for the next behaviour slice.
6. **Repeat** until the feature is complete.
7. **Refactor** — extract helpers, clean names, remove duplication. Keep tests green throughout.

**For bug fixes:** First write a test that reproduces the bug (it will fail). Then fix the bug. The test is the regression guard.

---

### What NOT to test

- Implementation details — test behaviour, not internal method calls.
- Third-party library internals (axios, Motor, Celery) — mock them at the boundary.
- Worker pipeline tasks directly — they require GPU/model files. Test the orchestration logic with mocked task functions instead.
- Pure rendering with no logic (static templates with no conditional or interaction).

---

## Running Tests (API)

```bash
cd api
pip install -r requirements.txt
pytest                          # all tests
pytest tests/test_routers_projects.py   # single file
pytest -k "test_name"           # single test
```

## Development Without Docker

```bash
# API
cd api && uvicorn app.main:app --reload --port 8000

# Worker (requires CUDA GPU)
cd worker && celery -A app.celery_app.celery worker --loglevel=info

# Frontend
cd frontend && npm install && npm run dev
```

## Architecture

### Services
| Service | Tech | Port |
|---|---|---|
| `frontend` | Vue 3 + Vite + Pinia | 5173 |
| `api` | FastAPI + Motor (async MongoDB) | 8000 |
| `worker` | Celery (solo pool, CUDA required) | — |
| `mongodb` | MongoDB | 27017 |
| `redis` | Redis 7 (Celery broker + pub/sub) | 6379 |
| `minio` | MinIO S3-compatible storage | 9000 |

### Request Flow

**Dubbing:**
1. Frontend uploads video → `POST /videos/upload` → stored in MinIO, recorded in MongoDB
2. `POST /jobs/dub?project_id=X&video_id=Y` → API fetches cached `vocals_url`, `no_vocals_url`, and existing transcription from MongoDB, then enqueues Celery task with all data as kwargs
3. Worker runs `dubbing_pipeline.dub_video` task; progress published to Redis pub/sub channel `job:{task_id}`
4. Frontend WebSocket connects to `WS /jobs/{task_id}/progress` → streams `{step, pct, message}`
5. On completion, worker uploads dubbed video + transcript to MinIO and returns full result (URLs, transcription text, segments, language, duration) via Celery result object — **no MongoDB access in worker**
6. `GET /jobs/{task_id}/status` polls Celery `AsyncResult`; on SUCCESS, API calls `persist_job_result()` to write to MongoDB (idempotent)

**Re-dubbing (skip transcription):**
- `POST /jobs/dub?skip_transcription=true` — API reads existing transcription + segments from MongoDB and passes them as kwargs; worker skips Demucs + Whisper

**Standalone transcription:**
- `POST /jobs/transcribe?project_id=X&video_id=Y` → API passes cached vocals URLs as kwargs; runs Demucs + Whisper only, no TTS

**Text-to-speech:**
- `POST /tts/generate` → synthesizes text using a built-in XTTS speaker (34 voices available)

### Key Architectural Decisions

- **VRAM management**: Whisper is pre-loaded at worker startup (`worker_process_init` signal). During a job, Whisper is explicitly released (`release_model()`) before loading XTTS v2 to avoid OOM on single-GPU machines. `release_model()` calls `del model`, `gc.collect()`, `torch.cuda.empty_cache()`.
- **Celery pool is `solo`**: Required because CUDA is not fork-safe. Only one task runs at a time per worker container.
- **Progress via Redis pub/sub**: Worker publishes JSON `{step, pct, message}` to `job:{task_id}`; also stores latest state with `SETEX` (1h TTL) in `job:{task_id}:latest` so WebSocket clients that connect late receive current state immediately.
- **MinIO URL rewriting**: Internal URLs use `minio:9000` hostname (Docker network); `S3_PUBLIC_ENDPOINT` rewrites to `localhost:9000` for browser-accessible presigned URLs.
- **Demucs vocal separation**: Uses `htdemucs` model (`--two-stems vocals`) to separate speech from background before transcription, improving Whisper accuracy.
- **Speaker reference from longest segments**: Voice reference WAV for XTTS is built by concatenating the longest speech segments until ≥8 seconds. Stereo is downmixed to mono before XTTS (which expects mono input).
- **Atempo stretch clamping**: TTS clips are time-stretched to match segment duration, but the ratio is clamped to [0.75, 1.5] to prevent unintelligible audio. Clips are hard-trimmed with a 50ms fade-out to prevent bleed.
- **Audio ducking**: Background track volume is ducked to a configurable level during speech segments and restored in silence.
- **Single Responsibility — worker is compute-only**: The worker has no MongoDB access. It receives all pre-fetched data (cached vocals URLs, existing transcription/segments) as Celery task kwargs from the API, performs AI computation and S3 uploads, then returns the full result (URLs, transcription text, segments, language, duration, job_id) via the Celery result object.
- **API owns all DB writes**: `GET /jobs/{task_id}/status` calls `persist_job_result()` on SUCCESS state, which idempotently writes to MongoDB (`$set` for fields, conditional `$push` for `dubbed_versions` keyed on `job_id` to prevent duplicates from repeated polling).
- **Vocal/background caching**: After first Demucs separation, worker uploads vocals and no-vocals to MinIO and returns their URLs in the result. API persists them to MongoDB. Subsequent re-dubs pass the cached URLs as kwargs — worker downloads directly from MinIO without re-running Demucs.

### Directory Layout

```
api/app/
  main.py              # FastAPI app, CORS, router registration
  config.py            # pydantic-settings Settings class
  routers/
    videos.py          # POST /videos/upload, GET /{id}/stream, GET /{id}/dubbed-stream
    projects.py        # CRUD for projects (YouTube download via yt-dlp)
    jobs.py            # POST /jobs/dub, POST /jobs/transcribe, GET /{id}/status, WS /{id}/progress
    tts.py             # GET /tts/voices, POST /tts/generate, GET /tts/{id}/status
  repositories/
    videos.py          # motor async MongoDB access; update_video_after_dub / update_video_after_transcribe
    projects.py
  services/
    jobs.py            # persist_job_result (DB write on SUCCESS), enrich_result (presigned URLs), register_job (Redis)
  models/              # Pydantic request/response schemas
    job.py
    project.py
    video.py
  utils/
    storage.py         # MinIO wrapper (boto3)
    queue.py           # Celery app instance (broker only, no tasks)
    database.py        # Motor MongoDB client
    youtube_metadata.py

worker/app/
  celery_app.py        # Celery instance; pre-loads Whisper on worker init
  config.py            # Worker pydantic-settings config
  storage.py           # MinIO storage client (no MongoDB — worker is compute-only)
  models/              # Structured data models
    audio.py           # Audio data model
    job.py             # Job model
    progress.py        # Progress tracking model
    segment.py         # Transcript segment model
  services/            # Business logic / infrastructure services
    audio_repository.py     # Audio file operations (MinIO)
    model_manager.py        # Model lifecycle (Whisper, XTTS load/release)
    progress_publisher.py   # Redis pub/sub progress publishing
    transcript_repository.py # Transcript storage
  pipelines/
    base.py                # Base pipeline class
    dubbing_pipeline.py    # Main @celery.task: full dub orchestration, publishes progress
    transcribe_pipeline.py # Standalone transcription task (no TTS)
    tts_pipeline.py        # Standalone TTS task using built-in speakers
  tasks/
    download.py        # Download video from MinIO to disk
    extract_audio.py   # ffmpeg audio extraction + Demucs vocal separation
    reference_audio.py # Voice reference WAV preparation for XTTS
    transcribe.py      # faster-whisper Whisper large-v3, translate=True by default
    tts.py             # XTTS v2: zero-shot voice cloning + built-in speaker synthesis
    audio_mix.py       # ffmpeg atempo time-stretch, duck + overlay mix, video mux
    upload.py          # Upload result files to MinIO

frontend/src/
  views/
    ProjectsView.vue        # Project list
    ProjectDetailView.vue   # Main workspace: dub, transcribe, re-dub, video player, transcript panel
    VideosView.vue          # Video listing within a project
    TextToSpeechView.vue    # TTS generation UI (speaker selection, audio playback)
    VoicesView.vue          # Browse available XTTS speakers
    SettingsView.vue
  stores/              # Pinia stores (projects, videos, jobs)
  api/                 # axios API client wrappers per resource (client.js, jobs.js, projects.js, tts.js, videos.js)
  components/          # Shared UI components (AppHeader, AppToast, DropZone, ProjectCard, SkeletonBlock,
                       #   TheSidebar, TopProgressBar, TranscriptPanel, VideoCard, VideoPlayer)
  composables/
    useToast.js        # Toast notification composable
  utils/
    url.js             # URL utilities
  router/
    index.js           # Vue Router configuration
```

### MongoDB Collections

- `projects` — `project_id`, YouTube metadata, timestamps
- `videos` — `video_id`, `project_id`, `video_url`, `vocals_url`, `no_vocals_url`, `transcription` (text), `transcript_url`, `dubbed_url`, timestamps

### MinIO Object Layout

```
{bucket}/
  {project_id}/video.mp4                    # original upload
  {project_id}/vocals_{job_id}.wav          # Demucs vocals (cached)
  {project_id}/no_vocals_{job_id}.wav       # Demucs background (cached)
  {project_id}/transcription_{job_id}.txt   # transcription text
  {project_id}/dubbed_{job_id}.mp4          # dubbed output
  tts/{job_id}.{wav|mp3}                    # standalone TTS output
```
