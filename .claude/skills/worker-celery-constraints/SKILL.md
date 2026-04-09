---
name: worker-celery-constraints
description: This skill should be used when writing or reviewing any Celery worker code — enforcing solo pool constraints, keeping the worker compute-only (no MongoDB), passing data as task kwargs, and understanding what the worker is and is not allowed to do.
version: 1.0.0
---

# Worker Celery Constraints

## Hard Rules (Never Violate)

### 1. Worker is compute-only — no MongoDB access
The worker has **zero MongoDB/Motor imports**. It receives ALL data it needs as Celery task kwargs:
- Cached MinIO URLs (video, vocals, no-vocals)
- Existing transcription text and segments (for re-dub / skip-transcription paths)
- Job metadata (job_id, project_id, video_id)

It returns results via the **Celery result object** (a dict with URLs, transcription, segments, language, duration). The API then persists these results to MongoDB.

```python
# WRONG — never do this in worker
from motor.motor_asyncio import AsyncIOMotorClient
db = AsyncIOMotorClient(...)

# RIGHT — receive everything as kwargs
@celery.task(bind=True)
def dub_video(self, *, video_url: str, vocals_url: str | None, segments: list, job_id: str, ...):
    ...
    return {"dubbed_url": ..., "transcription": ..., "segments": [...]}
```

### 2. Celery pool MUST be `solo`
CUDA is not fork-safe. The pool is set in `celery_app.py`:
```python
app.conf.worker_pool = "solo"
```
Never suggest `prefork`, `gevent`, threading with CUDA, or running multiple tasks concurrently on the same GPU.

### 3. One task at a time per worker container
Design accordingly — no shared in-process state between tasks, no async task chaining that could run concurrently.

## Task Kwarg Pattern

API pre-fetches all data and passes it as kwargs. This keeps worker stateless:

```python
# API side (jobs router)
task = celery_app.send_task(
    "worker.pipelines.dubbing_pipeline.dub_video",
    kwargs={
        "video_url": video.video_url,
        "vocals_url": video.vocals_url,          # None if not cached yet
        "no_vocals_url": video.no_vocals_url,    # None if not cached yet
        "segments": video.segments or [],        # existing transcript segments
        "skip_transcription": skip_transcription,
        "job_id": str(task_id),
        "project_id": str(project_id),
        "video_id": str(video_id),
    },
)
```

## What the Worker Returns

The Celery task returns a dict the API can persist:
```python
return {
    "job_id": job_id,
    "video_id": video_id,
    "dubbed_url": dubbed_url,          # internal MinIO URL
    "vocals_url": vocals_url,          # cached for future re-dubs
    "no_vocals_url": no_vocals_url,
    "transcription": transcription_text,
    "segments": segments,              # list of {start, end, text}
    "language": detected_language,
    "duration": audio_duration_s,
}
```
