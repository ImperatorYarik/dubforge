# Video Translation Website

A microservice web application that translates videos to English using AI (OpenAI Whisper), built with FastAPI, React/Next.js, MinIO, MongoDB, and Celery.

---

## Architecture

### Services Overview

```
┌─────────────┐     ┌─────────────┐     ┌──────────┐
│   Frontend  │────▶│  FastAPI    │────▶│ MongoDB  │
│  (React /   │     │   (API)     │     │          │
│  Next.js)   │     └──────┬──────┘     └──────────┘
└─────────────┘            │
                           │  enqueue job
                    ┌──────▼──────┐     ┌──────────┐
                    │    Redis    │     │  MinIO   │
                    │  (broker)   │     │ (storage)│
                    └──────┬──────┘     └────▲─────┘
                           │                 │
                    ┌──────▼──────┐          │
                    │   Worker    │──────────┘
                    │  (Celery)   │  upload/download
                    └─────────────┘
```

### Request Flow

1. **User uploads video** → Frontend → API → MinIO (stored as-is)
2. **API creates a job** in MongoDB (`status: pending`)
3. **API enqueues task** to Redis/Celery
4. **Worker picks up job:**
   - Downloads video from MinIO
   - Extracts audio via `ffmpeg`
   - Transcribes + translates with **OpenAI Whisper** (supports multilingual → English)
   - Generates `.srt` / `.vtt` subtitles
   - Optionally muxes subtitles into video
   - Uploads result to MinIO
   - Updates job `status: completed` in MongoDB
5. **Frontend polls** job status endpoint → shows result/download link

---

## Directory Layout

```
video-trans/
├── docker-compose.yml
├── .env.example
├── README.md
│
├── frontend/                        # React / Next.js
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   └── src/
│       ├── app/                     # Next.js App Router pages
│       │   ├── page.tsx             # Upload page
│       │   ├── jobs/[id]/page.tsx   # Job status/result page
│       │   └── layout.tsx
│       ├── components/
│       │   ├── VideoUploader.tsx
│       │   ├── JobStatus.tsx
│       │   └── VideoPlayer.tsx
│       └── services/
│           └── api.ts               # API client (axios/fetch)
│
├── api/                             # FastAPI backend
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                  # App entrypoint, CORS, routers
│       ├── config.py                # Settings (pydantic-settings)
│       ├── database.py              # MongoDB (motor async client)
│       ├── storage.py               # MinIO client wrapper
│       ├── queue.py                 # Celery app instance
│       ├── dependencies.py          # FastAPI deps (db, storage, auth)
│       ├── routers/
│       │   ├── videos.py            # POST /videos/upload
│       │   ├── jobs.py              # GET /jobs/{id}, GET /jobs/
│       │   └── auth.py              # POST /auth/register, /login
│       ├── models/                  # Pydantic request/response schemas
│       │   ├── video.py
│       │   ├── job.py
│       │   └── user.py
│       └── crud/                    # DB access layer
│           ├── jobs.py
│           └── users.py
│
├── worker/                          # Celery translation worker
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── celery_app.py            # Celery instance + config
│       ├── config.py
│       ├── storage.py               # MinIO client (shared with api)
│       ├── database.py              # MongoDB client
│       └── tasks/
│           ├── pipeline.py          # Main task: orchestrates steps
│           ├── extract_audio.py     # ffmpeg audio extraction
│           ├── transcribe.py        # Whisper transcription + translation
│           └── subtitles.py         # SRT/VTT generation + muxing
│
└── infra/
    ├── nginx/
    │   └── nginx.conf               # Reverse proxy (optional)
    └── minio/
        └── init.sh                  # Create default buckets on startup
```

---

## Key Technology Choices

| Concern | Choice | Why |
|---|---|---|
| Transcription + Translation | **OpenAI Whisper** (`faster-whisper`) | Single model handles both; multilingual → English built-in |
| Async task queue | **Celery + Redis** | Decouples upload from heavy AI processing |
| Video processing | **ffmpeg** (`ffmpeg-python`) | Reliable audio extraction and subtitle muxing |
| MongoDB driver | **Motor** (async) | Fits FastAPI's async model |
| MinIO client | **minio-py** | Official SDK |
| Auth | **JWT** (python-jose) | Stateless, works across services |

---

## MongoDB Collections

```
users   — _id, email, hashed_password, created_at
jobs    — _id, user_id, status, source_lang, created_at,
          input_object (MinIO key), output_object (MinIO key),
          transcript, error_message, updated_at
```

---

## MinIO Object Layout

```
uploads/<job_id>/original.mp4
results/<job_id>/translated.mp4   (or .srt / .vtt)
```

---

## Notes

- **Frontend and API are entirely separate** — communicate only via HTTP. Deploy independently.
- **Worker has no HTTP interface** — it only listens to Celery/Redis. Scale horizontally by adding more containers.
- Pre-signed MinIO URLs can be exposed for direct downloads instead of proxying through the API.
