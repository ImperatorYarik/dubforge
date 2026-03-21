# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

A microservice web application that dubs/translates videos to English using AI. The pipeline: downloads video → separates vocals (Demucs) → transcribes/translates (faster-whisper Whisper large-v3) → detects emotion per segment (wav2vec2) → synthesizes dubbed audio (XTTS v2 voice cloning) → time-stretches TTS to match original timing → mixes and muxes back into video.

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

1. Frontend uploads video → `POST /videos/upload` → stored in MinIO, recorded in MongoDB
2. `POST /jobs/dub?project_id=X&video_id=Y` → Celery task enqueued via Redis
3. Worker runs `dubbing_pipeline.dub_video` task; progress published to Redis pub/sub channel `job:{task_id}`
4. Frontend WebSocket connects to `GET /jobs/{task_id}/progress` → streams progress percentage
5. On completion, dubbed video and transcript uploaded to MinIO; result URLs returned in task result
6. `GET /jobs/{task_id}/status` polls Celery `AsyncResult` for final state

### Key Architectural Decisions

- **VRAM management**: Whisper is pre-loaded at worker startup (`worker_process_init` signal). During a job, Whisper is explicitly released (`release_model()`) before loading XTTS v2 to avoid OOM on single-GPU machines.
- **Celery pool is `solo`**: Required because CUDA is not fork-safe. Only one task runs at a time per worker container.
- **Progress via Redis pub/sub**: Worker publishes JSON `{step, pct, message}` to `job:{task_id}`; also stores latest state with `SETEX` (1h TTL) so WebSocket clients that connect late receive current state immediately.
- **MinIO URL rewriting**: Internal URLs use `minio:9000` hostname (Docker network); `S3_PUBLIC_ENDPOINT` rewrites to `localhost:9000` for browser-accessible presigned URLs.
- **Demucs vocal separation**: Uses `htdemucs` model (`--two-stems vocals`) to separate speech from background before transcription, improving Whisper accuracy.

### Directory Layout (actual, not README)

```
api/app/
  main.py              # FastAPI app, CORS, router registration
  config.py            # pydantic-settings Settings class
  routers/
    videos.py          # POST /videos/upload, GET /{id}/stream (presigned URL)
    projects.py        # CRUD for projects
    jobs.py            # POST /jobs/dub, GET /{id}/status, WS /{id}/progress
  CRUD/
    videos.py          # motor async MongoDB access
    projects.py
  models/              # Pydantic request/response schemas
  utils/
    storage.py         # MinIO wrapper (boto3)
    queue.py           # Celery app instance (broker only, no tasks)
    database.py        # Motor MongoDB client

worker/app/
  celery_app.py        # Celery instance; pre-loads Whisper on worker init
  pipelines/
    dubbing_pipeline.py  # Main @celery.task: orchestrates all steps, publishes progress
  tasks/
    download.py        # Download video from MinIO to disk
    extract_audio.py   # ffmpeg audio extraction + Demucs vocal separation
    transcribe.py      # faster-whisper Whisper large-v3, translate=True by default
    tts.py             # XTTS v2 zero-shot voice cloning synthesis
    emotion.py         # wav2vec2 emotion classifier per segment
    audio_mix.py       # rubberband time-stretch, duck + overlay mix, ffmpeg mux
    upload.py          # Upload result files to MinIO

frontend/src/
  views/               # Vue Router pages (Projects, ProjectDetail, Videos, etc.)
  stores/              # Pinia stores (projects, videos, jobs)
  api/                 # axios API client wrappers per resource
  components/          # Shared UI components
```

### MongoDB Collections

- `projects` — project metadata
- `videos` — `_id, project_id, video_url` (MinIO URL), metadata

### MinIO Object Layout

```
{bucket}/
  {project_id}/{video_id}.{ext}          # original upload
  {project_id}/dubbed_{job_id}.{ext}     # dubbed output
  {project_id}/transcription_{job_id}.txt
```
