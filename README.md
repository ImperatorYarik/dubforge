# Video Dubbing App

A microservice web application that dubs videos to English using AI. Upload a video (or import from YouTube), and the pipeline automatically separates vocals, transcribes and translates speech, clones the original voice, synthesizes dubbed audio, and muxes it back into the video — all with real-time progress updates.

---

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
   - [Service Map](#service-map)
   - [Dubbing Pipeline](#dubbing-pipeline)
   - [Request Flow](#request-flow)
3. [Prerequisites](#prerequisites)
4. [Setup Runbook](#setup-runbook)
   - [Step 1 — Clone the repository](#step-1--clone-the-repository)
   - [Step 2 — Create the environment file](#step-2--create-the-environment-file)
   - [Step 3 — Configure local DNS](#step-3--configure-local-dns-etchosts)
   - [Step 4 — Start infrastructure services](#step-4--start-infrastructure-services)
   - [Step 5 — Verify services are healthy](#step-5--verify-services-are-healthy)
   - [Step 6 — Start the worker (GPU required)](#step-6--start-the-worker-gpu-required)
   - [Step 7 — Open the app](#step-7--open-the-app)
5. [Service Reference](#service-reference)
6. [API Endpoints](#api-endpoints)
7. [Storage Layout](#storage-layout)
8. [Database Collections](#database-collections)
9. [Key Technical Decisions](#key-technical-decisions)
10. [Directory Layout](#directory-layout)
11. [Claude Code Setup](#claude-code-setup)
    - [Recommended Claude Code Configuration](#recommended-claude-code-configuration)
    - [TDD Workflow](#tdd-workflow)
    - [Running Tests](#running-tests)

---

## Features

### Core Pipeline
- **Vocal separation** via Demucs (`htdemucs`, `--two-stems vocals`) — isolates speech from background before transcription
- **Transcription + translation** via faster-whisper (Whisper large-v3, int8 quantized) — multilingual → English
- **Zero-shot voice cloning** via XTTS v2 — clones the original speaker's voice from source audio
- **Time-stretch** TTS clips to match original segment timing (ffmpeg atempo, clamped to 0.75–1.5×)
- **Audio ducking** — background track is lowered during speech and restored in silence
- **Video remux** — stream-copies video, replaces audio track (no re-encode)

### Additional Features
- **Re-dub** — re-synthesize TTS reusing existing transcription (skips Demucs + Whisper)
- **Standalone transcription** — run Demucs + Whisper without dubbing
- **Text-to-speech** — generate audio from text using 34 built-in XTTS voices (17F + 17M)
- **YouTube import** — create projects directly from a YouTube URL via yt-dlp
- **Vocal/background caching** — Demucs results stored in MinIO; re-dubs reuse them
- **Real-time progress** via WebSocket (Redis pub/sub) with late-join support

---

## Architecture

### Service Map

```
┌──────────────────────────────────────────────────────────────────┐
│                          Browser                                  │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTP / WebSocket
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│                     Frontend  :5173                               │
│              Vue 3 + Vite + Pinia + axios                         │
└───────────────────────────┬───────────────────────────────────────┘
                            │ REST + WebSocket
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│                       API  :8000                                  │
│               FastAPI + Motor (async MongoDB)                     │
└────────┬──────────────────┬──────────────────┬────────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
  ┌─────────────┐   ┌──────────────┐   ┌─────────────┐
  │  MongoDB    │   │    Redis     │   │    MinIO    │
  │  :27017     │   │    :6379     │   │ :9000/:9001 │
  │  (metadata) │   │ (broker +   │   │  (files)    │
  └─────────────┘   │  pub/sub)   │   └──────┬──────┘
                    └──────┬───────┘          │
                           │ task queue        │ upload/download
                           ▼                  │
                    ┌─────────────┐           │
                    │   Worker    │◀──────────┘
                    │  (Celery)   │
                    │  CUDA GPU   │
                    └─────────────┘
```

### Dubbing Pipeline

```
Input video
     │
     ▼
┌─────────────────────┐
│  1. Download        │  MinIO → worker disk
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  2. Extract audio   │  ffmpeg → raw audio
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  3. Demucs          │  htdemucs --two-stems vocals
│  vocal separation   │  → vocals.wav + no_vocals.wav (cached in MinIO)
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  4. Whisper         │  faster-whisper large-v3 (int8)
│  transcribe/translate│  multilingual → English segments
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  5. Build voice ref │  concat longest segments until ≥8s
│  (XTTS reference)   │  stereo → mono downmix
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  6. XTTS v2         │  zero-shot voice cloning per segment
│  TTS synthesis      │  Whisper released from VRAM first
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  7. Audio mix       │  atempo stretch [0.75–1.5×] + 50ms fade
│  time-stretch + duck│  background ducked during speech
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  8. Mux + upload    │  ffmpeg stream-copy video + dubbed audio
│                     │  → MinIO; full result returned via Celery
│                     │  API writes to MongoDB on GET /status poll
└─────────────────────┘
```

### Request Flow

**Dubbing job:**
```
Frontend ──POST /videos/upload──▶ API ──▶ MinIO (store video)
                                      └──▶ MongoDB (record video)

Frontend ──POST /jobs/dub──▶ API ──reads──▶ MongoDB (vocals_url, existing transcription)
                                 └──▶ Redis (enqueue task with cached data as kwargs)
                                 └──▶ returns { task_id }

Frontend ──WS /jobs/{id}/progress──▶ API ──▶ Redis sub (stream events)
                                         ──▶ Browser progress bar

Worker ──publishes──▶ Redis pub/sub channel job:{task_id}
       ──uploads────▶ MinIO (dubbed video, transcript, vocals if new)
       ──returns────▶ Celery result (URLs + transcription + segments + language)
       (no MongoDB access)

Frontend ──GET /jobs/{id}/status──▶ API ──▶ Celery AsyncResult
                                       └── on SUCCESS ──▶ MongoDB (persist_job_result, idempotent)
                                                      └──▶ returns enriched result with presigned URLs
```

---

## Prerequisites

| Requirement | Minimum version | Notes |
|---|---|---|
| Docker Engine | 24.x | [Install guide](https://docs.docker.com/engine/install/) |
| Docker Compose | v2.x (`docker compose`) | Bundled with Docker Desktop |
| NVIDIA GPU | Any CUDA-capable card | Required for worker only |
| NVIDIA Container Toolkit | latest | `nvidia-docker2` — [Install guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) |
| VRAM | ≥8 GB recommended | Whisper large-v3 + XTTS v2 loaded sequentially |
| Disk space | ≥20 GB | AI model weights downloaded on first run |

> **No GPU?** You can still run the frontend, API, and all infrastructure — just skip the worker. Dubbing/transcription jobs won't execute, but you can explore the UI and API.

---

## Setup Runbook

### Step 1 — Clone the repository

```bash
git clone <repo-url> video-trans
cd video-trans
```

### Step 2 — Create the environment file

Copy the template and fill in required values:

```bash
cp .env.example .env   # if .env.example exists, otherwise create .env manually
```

Edit `.env`:

```dotenv
# Infrastructure (use these exact values for local Docker setup)
MONGO_URI=mongodb://mongodb:27017
S3_ENDPOINT=http://minio:9000
S3_PUBLIC_ENDPOINT=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
REDIS_URL=redis://redis:6379/0

# Security — generate a strong random string
JWT_SECRET_KEY=change-me-to-a-strong-random-secret

# Worker — required for XTTS v2 licensing
COQUI_TOS_AGREED=1

# Optional — speeds up Hugging Face model downloads (get token at huggingface.co)
HF_TOKEN=
```

> `S3_PUBLIC_ENDPOINT` must be reachable from your browser. Use `http://localhost:9000` for local dev.

### Step 3 — Configure local DNS (`/etc/hosts`)

An nginx reverse proxy is included in the dev stack that routes requests by subdomain. Add the following entries to `/etc/hosts` (requires `sudo`):

```bash
sudo tee -a /etc/hosts <<'EOF'

# dubforge local dev
127.0.0.1 dubforge.local
127.0.0.1 api.dubforge.local
127.0.0.1 grafana.dubforge.local
127.0.0.1 prometheus.dubforge.local
127.0.0.1 minio.dubforge.local
127.0.0.1 minio-console.dubforge.local
127.0.0.1 loki.dubforge.local
EOF
```

After adding these, the services are accessible at:

| Subdomain | Service |
|---|---|
| http://dubforge.local | Frontend |
| http://api.dubforge.local | API + Swagger docs (`/docs`) |
| http://grafana.dubforge.local | Grafana dashboards |
| http://prometheus.dubforge.local | Prometheus |
| http://minio.dubforge.local | MinIO S3 API |
| http://minio-console.dubforge.local | MinIO Web Console |
| http://loki.dubforge.local | Loki |

> Direct port access still works (e.g. `localhost:8000`) if you prefer to skip nginx.

### Step 4 — Start infrastructure services

**Option A — Full stack with GPU worker:**

```bash
docker compose up --build
```

**Option B — Without GPU (frontend + API + storage only):**

```bash
docker compose up --build frontend api mongodb redis minio
```

Docker will:
1. Build the `frontend`, `api`, and `worker` images
2. Pull `mongo:latest`, `redis:7-alpine`, `minio/minio:latest`
3. Start all containers on the `project_network` bridge

> First startup downloads AI model weights (~5–10 GB). This can take 10–30 minutes depending on your connection. Subsequent startups are fast.

### Step 5 — Verify services are healthy

Check all containers are running:

```bash
docker compose ps
```

Expected output (all containers should show `running` or `Up`):

```
NAME                    STATUS
video-trans-frontend    Up
video-trans-api         Up
video-trans-worker      Up   ← only if GPU option used
mongodb                 Up
minio                   Up
redis                   Up
```

Spot-check each service:

```bash
# API health
curl http://localhost:8000/docs        # FastAPI Swagger UI should load

# MinIO console
open http://localhost:9001             # login: minioadmin / minioadmin

# MongoDB
docker exec -it mongodb mongosh --eval "db.adminCommand('ping')"
```

View logs for a specific service:

```bash
docker compose logs -f api             # follow API logs
docker compose logs -f worker          # follow worker / model loading progress
```

### Step 6 — Start the worker (GPU required)

If you started with Option B and later want to enable the worker:

```bash
# Verify NVIDIA Container Toolkit is set up
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi

# Start the worker service
docker compose up --build worker
```

The worker logs will show model download and load progress:

```
[Worker] Loading Whisper large-v3...
[Worker] Whisper ready. Worker accepting tasks.
```

### Step 7 — Open the app

| Service | URL (subdomain) | URL (direct port) | Credentials |
|---|---|---|---|
| Frontend | http://dubforge.local | http://localhost:5173 | — |
| API docs (Swagger) | http://api.dubforge.local/docs | http://localhost:8000/docs | — |
| Grafana | http://grafana.dubforge.local | http://localhost:3000 | `admin` / `admin` |
| Prometheus | http://prometheus.dubforge.local | http://localhost:9090 | — |
| MinIO console | http://minio-console.dubforge.local | http://localhost:9001 | `minioadmin` / `minioadmin` |
| Loki | http://loki.dubforge.local | http://localhost:3100 | — |

**Quick first-use flow:**
1. Open http://localhost:5173
2. Create a project (upload a video file or paste a YouTube URL)
3. Click **Dub** to start the pipeline
4. Watch the real-time progress bar
5. Play the dubbed video side-by-side with the original

---

## Service Reference

| Service | Container | Port | Tech | Notes |
|---|---|---|---|---|
| `frontend` | `video-trans-frontend` | 5173 | Vue 3 + Vite + Pinia | Vite dev server on port 80 inside container |
| `api` | `video-trans-api` | 8000 | FastAPI + Motor | Auto-reload enabled (`--reload`) |
| `worker` | `video-trans-worker` | — | Celery (solo pool) | Requires NVIDIA GPU |
| `mongodb` | `mongodb` | 27017 | MongoDB latest | Data persisted in `mongo_data` volume |
| `redis` | `redis` | 6379 | Redis 7 Alpine | Celery broker + pub/sub |
| `minio` | `minio` | 9000 / 9001 | MinIO | S3-compatible; data in `minio_data` volume |
| `nginx` | `nginx` | 80 | nginx:alpine | Reverse proxy — subdomain routing (dev only, via override) |
| `prometheus` | `prometheus` | 9090 | Prometheus | Metrics scraping (dev only, via override) |
| `grafana` | `grafana` | 3000 | Grafana | Dashboards — `admin`/`admin` (dev only, via override) |
| `loki` | `loki` | 3100 | Grafana Loki | Log aggregation (dev only, via override) |
| `promtail` | `promtail` | — | Grafana Promtail | Ships Docker container logs to Loki (dev only, via override) |
| `redis-exporter` | `redis-exporter` | 9121 | oliver006/redis_exporter | Exports Redis metrics to Prometheus |
| `mongodb-exporter` | `mongodb-exporter` | 9216 | percona/mongodb_exporter | Exports MongoDB metrics to Prometheus |
| `node-exporter` | `node-exporter` | 9100 | prom/node-exporter | Exports host system metrics |
| `nvidia-gpu-exporter` | `nvidia-gpu-exporter` | 9835 | utkuozdemir/nvidia_gpu_exporter | Exports GPU metrics |

**Useful commands:**

```bash
# Stop all services
docker compose down

# Stop and delete volumes (wipes all data)
docker compose down -v

# Rebuild a single service after code change
docker compose up -d --build api

# Shell into a running container
docker exec -it video-trans-api bash
docker exec -it video-trans-worker bash

# Tail all logs
docker compose logs -f
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/projects/create` | Create project (YouTube URL or manual) |
| `GET` | `/projects/list_projects` | List all projects |
| `DELETE` | `/projects/{id}` | Delete project + MinIO cleanup |
| `POST` | `/videos/upload` | Upload video file |
| `GET` | `/videos/{id}/stream` | Presigned URL for original video |
| `GET` | `/videos/{id}/dubbed-stream` | Presigned URL for dubbed video |
| `POST` | `/jobs/dub` | Start dubbing job |
| `POST` | `/jobs/transcribe` | Start transcription-only job |
| `GET` | `/jobs/{id}/status` | Poll job status (Celery AsyncResult) |
| `WS` | `/jobs/{id}/progress` | Stream real-time progress events |
| `GET` | `/tts/voices` | List available XTTS speakers |
| `POST` | `/tts/generate` | Generate TTS audio from text |
| `GET` | `/tts/{id}/status` | Poll TTS job status |

Full interactive docs: http://localhost:8000/docs

---

## Storage Layout

MinIO bucket structure:

```
{bucket}/
  {project_id}/
    video.mp4                        # original upload
    vocals_{job_id}.wav              # Demucs vocals (cached — reused on re-dub)
    no_vocals_{job_id}.wav           # Demucs background (cached)
    transcription_{job_id}.txt       # transcript text
    dubbed_{job_id}.mp4              # dubbed output video
  tts/
    {job_id}.wav                     # standalone TTS output
    {job_id}.mp3
```

---

## Database Collections

**`projects`**

| Field | Type | Description |
|---|---|---|
| `project_id` | string | Unique project identifier |
| `title` | string | Project / video title |
| `youtube_url` | string | Source YouTube URL (if imported) |
| `created_at` | datetime | Creation timestamp |

**`videos`**

| Field | Type | Description |
|---|---|---|
| `video_id` | string | Unique video identifier |
| `project_id` | string | Parent project |
| `video_url` | string | MinIO path for original video |
| `vocals_url` | string | MinIO path for Demucs vocals (cached) |
| `no_vocals_url` | string | MinIO path for Demucs background (cached) |
| `transcription` | string | Full transcript text |
| `transcript_url` | string | MinIO path for transcript file |
| `dubbed_url` | string | MinIO path for dubbed video |
| `created_at` | datetime | Upload timestamp |

---

## Key Technical Decisions

| Concern | Choice | Reason |
|---|---|---|
| Vocal separation | Demucs `htdemucs` | Significantly improves Whisper accuracy on noisy audio |
| Transcription | faster-whisper large-v3 (int8) | Best accuracy; int8 saves VRAM vs fp16 |
| Voice synthesis | XTTS v2 zero-shot | No speaker training required — works from reference audio |
| VRAM management | Explicit model release between Whisper → XTTS | Single-GPU machines would OOM with both loaded |
| Task queue | Celery + Redis (solo pool) | CUDA is not fork-safe; solo pool ensures one task at a time |
| Progress streaming | Redis pub/sub + WebSocket | Real-time; late-joining clients get cached latest state via `SETEX` |
| Storage | MinIO (S3-compatible) | Local S3; presigned URLs enable direct browser playback |
| Worker responsibility | Compute + S3 uploads only | No MongoDB in worker — API resolves cached data before enqueueing and persists results on `GET /status` (idempotent `$set` + conditional `$push`) |
| Frontend state | Pinia | Vue 3 idiomatic; simpler than Vuex |

---

## Directory Layout

```
video-trans/
├── .env                             # environment variables (not committed)
├── docker-compose.yaml
│
├── api/                             # FastAPI backend
│   └── app/
│       ├── main.py                  # app factory, CORS, router registration
│       ├── config.py                # pydantic-settings Settings
│       ├── routers/
│       │   ├── videos.py            # upload, stream endpoints
│       │   ├── projects.py          # CRUD + YouTube import
│       │   ├── jobs.py              # dub, transcribe, status, WebSocket
│       │   └── tts.py               # voices, generate, status
│       ├── repositories/
│       │   ├── videos.py            # Motor async DB access; update_video_after_dub/transcribe
│       │   └── projects.py
│       ├── services/
│       │   └── jobs.py              # persist_job_result, enrich_result, register_job
│       ├── models/                  # Pydantic request/response schemas
│       └── utils/
│           ├── storage.py           # MinIO wrapper (boto3)
│           ├── queue.py             # Celery app instance (broker only)
│           ├── database.py          # Motor MongoDB client
│           └── youtube_metadata.py
│
├── worker/                          # Celery background worker (CUDA) — compute + S3 only, no MongoDB
│   └── app/
│       ├── celery_app.py            # Celery instance; Whisper pre-loaded on init
│       ├── config.py
│       ├── pipelines/
│       │   ├── dubbing_pipeline.py  # Main @celery.task — full dub orchestration
│       │   ├── transcribe_pipeline.py
│       │   └── tts_pipeline.py
│       ├── tasks/
│       │   ├── download.py          # MinIO → worker disk
│       │   ├── extract_audio.py     # ffmpeg + Demucs
│       │   ├── reference_audio.py   # voice reference WAV for XTTS
│       │   ├── transcribe.py        # faster-whisper (VRAM-managed)
│       │   ├── tts.py               # XTTS v2 (VRAM-managed)
│       │   ├── audio_mix.py         # atempo stretch, duck, mux
│       │   └── upload.py            # disk → MinIO
│       └── services/
│           ├── model_manager.py     # Whisper/XTTS load + release lifecycle
│           ├── progress_publisher.py # Redis pub/sub publishing
│           ├── audio_repository.py
│           └── transcript_repository.py
│
├── frontend/                        # Vue 3 + Vite
│   └── src/
│       ├── views/
│       │   ├── ProjectsView.vue
│       │   ├── ProjectDetailView.vue  # main workspace
│       │   ├── TextToSpeechView.vue
│       │   └── VoicesView.vue
│       ├── stores/                  # Pinia (projects, videos, jobs)
│       ├── api/                     # axios wrappers per resource
│       ├── components/              # VideoPlayer, TranscriptPanel, etc.
│       ├── composables/
│       └── router/
│
└── infra/
    └── nginx/                       # optional reverse proxy config
```

---

## Claude Code Setup

This project is configured for [Claude Code](https://claude.ai/code) with full TDD enforcement. Follow these steps before starting development.

### Step 1 — Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

### Step 2 — Authenticate

```bash
claude
# Follow the OAuth prompts to authenticate with your Anthropic account
```

### Step 3 — Open the project

```bash
cd video-trans
claude          # starts Claude Code in this directory
```

Claude Code will automatically load `CLAUDE.md` — this file contains all project conventions, TDD rules, and architectural context.

### Step 4 — Verify Claude Code reads project context

Ask Claude Code:
```
What does this project do and what TDD rules apply?
```

It should describe the dubbing pipeline and the Red-Green-Refactor cycle without you explaining anything.

### Recommended Claude Code Configuration

The `CLAUDE.md` enforces the following rules that Claude Code will follow automatically:

| Rule | Details |
|---|---|
| TDD required | Write failing test first, then minimum production code, then refactor |
| Mock at router boundary | Patch `app.routers.<module>.<dependency>`, not the underlying DB driver |
| No extra features | Write only what the failing test requires — no preemptive abstractions |
| No implementation detail tests | Test behaviour/contracts, not internal method calls |
| Worker tasks not tested directly | Require GPU — mock at the orchestration layer instead |

### TDD Workflow

```
1. RED    Write a failing test describing desired behaviour
          Run: pytest -x  (API)  or  npm run test -- --watch  (frontend)
          Confirm it fails with a meaningful error

2. GREEN  Write minimum production code to pass the test
          Run tests again — should be green

3. REFACTOR  Clean up, extract helpers, remove duplication
             Keep tests green throughout
```

**For bug fixes:** write a test that reproduces the bug first (it will fail), then fix — the test becomes the regression guard.

### Running Tests

**API (pytest):**

```bash
cd api
pip install -r requirements.txt

pytest                                    # all tests
pytest tests/test_routers_projects.py     # single file
pytest -k "test_success"                  # single test by name
pytest -x                                 # stop on first failure (use during RED phase)
pytest --tb=short                         # brief tracebacks
```

**Frontend (Vitest):**

```bash
cd frontend
npm run test                              # run once
npm run test -- --watch                   # watch mode during development
npm run test -- --reporter=verbose        # per-test output
```

**After editing a service, rebuild its container:**

```bash
docker compose up -d --build api          # after editing api/
docker compose up -d --build worker       # after editing worker/
# frontend hot-reloads automatically in dev; rebuild only needed for prod image
```
