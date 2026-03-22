# Video Dubbing App

A microservice web application that dubs videos to English using AI. Upload a video (or import from YouTube), and the pipeline automatically separates vocals, transcribes and translates speech, clones the original voice, synthesizes dubbed audio, and muxes it back into the video — all with real-time progress updates.

---

## What's Implemented

### Core Pipeline
- **Vocal separation** via Demucs (`htdemucs`, `--two-stems vocals`) — isolates speech from background before transcription
- **Transcription + translation** via faster-whisper (Whisper large-v3, int8 quantized) — multilingual → English
- **Zero-shot voice cloning** via XTTS v2 — clones the original speaker's voice from the source audio
- **Time-stretch** TTS clips to match original segment timing (ffmpeg atempo, clamped to 0.75–1.5× for intelligibility)
- **Audio ducking** — background track is lowered during speech segments and restored in silence
- **Video remux** — stream-copies video, replaces audio track (no re-encode)

### Additional Features
- **Re-dub** — re-synthesize TTS using the existing transcription (skips Demucs + Whisper)
- **Standalone transcription** — run Demucs + Whisper without dubbing
- **Text-to-speech** — generate audio from text using 34 built-in XTTS voices (17F + 17M)
- **YouTube import** — create projects directly from a YouTube URL via yt-dlp
- **Vocal/background caching** — Demucs results are stored in MinIO; re-dubs reuse them
- **Real-time progress** via WebSocket (Redis pub/sub) with late-join support

### Frontend (Vue 3 + Vite + Pinia)
- Project management workspace with side-by-side original/dubbed video player
- Transcript panel with timestamps
- Dub / Transcribe / Re-dub actions with live progress bar
- Text-to-speech page with speaker selection and audio playback
- Voices browser (34 available speakers)

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────┐
│   Frontend  │────▶│  FastAPI    │────▶│ MongoDB  │
│  (Vue 3 +   │ WS  │   (API)     │     │          │
│   Vite)     │◀────│             │     └──────────┘
└─────────────┘     └──────┬──────┘
                           │  enqueue job
                    ┌──────▼──────┐     ┌──────────┐
                    │    Redis    │     │  MinIO   │
                    │  (broker +  │     │ (storage)│
                    │   pub/sub)  │     └────▲─────┘
                    └──────┬──────┘          │
                           │                 │
                    ┌──────▼──────┐          │
                    │   Worker    │──────────┘
                    │  (Celery)   │  upload/download
                    └─────────────┘
```

### Services

| Service | Tech | Port |
|---|---|---|
| `frontend` | Vue 3 + Vite + Pinia | 5173 |
| `api` | FastAPI + Motor (async MongoDB) | 8000 |
| `worker` | Celery (solo pool, CUDA required) | — |
| `mongodb` | MongoDB | 27017 |
| `redis` | Redis 7 (Celery broker + pub/sub) | 6379 |
| `minio` | MinIO S3-compatible storage | 9000 / 9001 |

### API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/projects/create` | Create project (YouTube URL or upload) |
| `GET` | `/projects/list_projects` | List all projects |
| `DELETE` | `/projects/{id}` | Delete project + MinIO cleanup |
| `POST` | `/videos/upload` | Upload video file |
| `GET` | `/videos/{id}/stream` | Presigned URL for original video |
| `GET` | `/videos/{id}/dubbed-stream` | Presigned URL for dubbed video |
| `POST` | `/jobs/dub` | Start dubbing job |
| `POST` | `/jobs/transcribe` | Start transcription-only job |
| `GET` | `/jobs/{id}/status` | Poll job status |
| `WS` | `/jobs/{id}/progress` | Stream real-time progress |
| `GET` | `/tts/voices` | List available speakers |
| `POST` | `/tts/generate` | Generate TTS audio |
| `GET` | `/tts/{id}/status` | Poll TTS job status |

---

## Running the Stack

```bash
# Start all services (requires CUDA GPU for worker)
docker compose up --build

# Start without GPU (frontend + API only, no dubbing)
docker compose up frontend api mongodb redis minio
```

Required `.env` variables:
```
MONGO_URI=mongodb://mongodb:27017
S3_ENDPOINT=http://minio:9000
S3_PUBLIC_ENDPOINT=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
JWT_SECRET_KEY=<secret>
REDIS_URL=redis://redis:6379/0
HF_TOKEN=<huggingface token>   # optional, speeds up model downloads
COQUI_TOS_AGREED=1             # required for XTTS v2
```

---

## Directory Layout

```
video-trans/
├── docker-compose.yaml
├── api/                         # FastAPI backend
│   └── app/
│       ├── main.py
│       ├── routers/             # videos, projects, jobs, tts
│       ├── CRUD/                # Motor async DB access
│       ├── models/              # Pydantic schemas
│       └── utils/               # MinIO, MongoDB, Celery clients
│
├── worker/                      # Celery background worker (CUDA)
│   └── app/
│       ├── celery_app.py        # Whisper pre-loaded on startup
│       ├── pipelines/
│       │   ├── dubbing_pipeline.py    # Full dub orchestration
│       │   ├── transcribe_pipeline.py # Transcription only
│       │   └── tts_pipeline.py        # Built-in speaker TTS
│       └── tasks/
│           ├── download.py      # MinIO → disk
│           ├── extract_audio.py # ffmpeg + Demucs
│           ├── transcribe.py    # faster-whisper (VRAM-managed)
│           ├── tts.py           # XTTS v2 (VRAM-managed)
│           ├── audio_mix.py     # atempo stretch, duck, mux
│           └── upload.py        # disk → MinIO
│
├── frontend/                    # Vue 3 + Vite
│   └── src/
│       ├── views/               # ProjectDetail, TTS, Voices, Settings
│       ├── stores/              # Pinia (projects, videos, jobs)
│       ├── api/                 # axios wrappers
│       └── components/          # VideoPlayer, TranscriptPanel, etc.
│
└── infra/
    └── nginx/                   # Optional reverse proxy
```

---

## Key Technical Decisions

| Concern | Choice | Reason |
|---|---|---|
| Vocal separation | **Demucs** `htdemucs` | Significantly improves Whisper accuracy on speech |
| Transcription | **faster-whisper** large-v3 (int8) | Best accuracy; int8 quantization saves VRAM |
| Voice synthesis | **XTTS v2** zero-shot cloning | No speaker training required |
| VRAM management | Explicit model release between Whisper → XTTS | Single-GPU machines would OOM otherwise |
| Task queue | **Celery + Redis** (solo pool) | CUDA is not fork-safe; solo pool prevents issues |
| Progress streaming | **Redis pub/sub** + WebSocket | Real-time updates; late-joining clients get cached state |
| Storage | **MinIO** (S3-compatible) | Local S3; presigned URLs for direct browser playback |
| Frontend state | **Pinia** | Vue 3 idiomatic state management |

---

## Running Tests (API)

```bash
cd api
pip install -r requirements.txt
pytest                                       # all tests
pytest tests/test_routers_projects.py        # single file
pytest -k "test_name"                        # single test
```

---

## Development Without Docker

```bash
# API
cd api && uvicorn app.main:app --reload --port 8000

# Worker (requires CUDA GPU)
cd worker && celery -A app.celery_app.celery worker --loglevel=info

# Frontend
cd frontend && npm install && npm run dev
```
