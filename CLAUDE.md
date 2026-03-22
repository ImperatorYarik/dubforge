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
2. `POST /jobs/dub?project_id=X&video_id=Y` → Celery task enqueued via Redis
3. Worker runs `dubbing_pipeline.dub_video` task; progress published to Redis pub/sub channel `job:{task_id}`
4. Frontend WebSocket connects to `WS /jobs/{task_id}/progress` → streams `{step, pct, message}`
5. On completion, dubbed video + transcript uploaded to MinIO; URLs stored in MongoDB
6. `GET /jobs/{task_id}/status` polls Celery `AsyncResult` for final state

**Re-dubbing (skip transcription):**
- `POST /jobs/dub?skip_transcription=true` — reuses existing transcription from MongoDB, only re-synthesizes TTS

**Standalone transcription:**
- `POST /jobs/transcribe?project_id=X&video_id=Y` → runs Demucs + Whisper only, no TTS

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
- **Vocal/background caching**: After first Demucs separation, vocals and no-vocals are uploaded to MinIO and their URLs stored in MongoDB. Subsequent re-dubs download these cached files instead of re-running Demucs.

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
  CRUD/
    videos.py          # motor async MongoDB access
    projects.py
  models/              # Pydantic request/response schemas
  utils/
    storage.py         # MinIO wrapper (boto3)
    queue.py           # Celery app instance (broker only, no tasks)
    database.py        # Motor MongoDB client
    youtube_metadata.py

worker/app/
  celery_app.py        # Celery instance; pre-loads Whisper on worker init
  pipelines/
    dubbing_pipeline.py    # Main @celery.task: full dub orchestration, publishes progress
    transcribe_pipeline.py # Standalone transcription task (no TTS)
    tts_pipeline.py        # Standalone TTS task using built-in speakers
  tasks/
    download.py        # Download video from MinIO to disk
    extract_audio.py   # ffmpeg audio extraction + Demucs vocal separation
    transcribe.py      # faster-whisper Whisper large-v3, translate=True by default
    tts.py             # XTTS v2: zero-shot voice cloning + built-in speaker synthesis
    audio_mix.py       # ffmpeg atempo time-stretch, duck + overlay mix, video mux
    upload.py          # Upload result files to MinIO

frontend/src/
  views/
    ProjectsView.vue        # Project list
    ProjectDetailView.vue   # Main workspace: dub, transcribe, re-dub, video player, transcript panel
    TextToSpeechView.vue    # TTS generation UI (speaker selection, audio playback)
    VoicesView.vue          # Browse available XTTS speakers
    SettingsView.vue
  stores/              # Pinia stores (projects, videos, jobs)
  api/                 # axios API client wrappers per resource
  components/          # Shared UI components (VideoPlayer, TranscriptPanel, DropZone, etc.)
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
