---
name: api-integrations
description: This skill should be used when writing API code that interacts with MinIO (presigned URLs, URL rewriting), Celery (task enqueueing, AsyncResult polling, job persistence), or Redis (job registration for WebSocket streaming).
version: 1.0.0
---

# External Integrations: MinIO, Celery, Redis

## MinIO / S3

**URL rewriting rule:** Internal MinIO URLs use `minio:9000` (Docker network). All media URLs returned to the browser must use `S3_PUBLIC_ENDPOINT` (e.g. `localhost:9000`).

```python
def rewrite_url(internal_url: str, settings: Settings) -> str:
    return internal_url.replace("http://minio:9000", settings.S3_PUBLIC_ENDPOINT)
```

**Presigned URLs** — always use presigned URLs for media responses, with appropriate TTL:
```python
url = storage.generate_presigned_url(bucket, key, expires_in=3600)
public_url = rewrite_url(url, settings)
```

**Error handling** — wrap MinIO operations in try/except and propagate as service-layer errors (not `HTTPException`):
```python
try:
    url = storage.get_presigned_url(key)
except Exception as exc:
    raise RuntimeError(f"Storage unavailable: {exc}") from exc
```

## Celery

**API role** — only enqueues tasks and reads `AsyncResult`. Never imports or executes task logic:
```python
from app.utils.queue import celery_app

result = celery_app.send_task(
    "worker.pipelines.dubbing_pipeline.dub_video",
    kwargs={"video_url": url, "vocals_url": vocals_url, "segments": segments},
)
task_id = result.id
```

**Pass all data as kwargs** — API pre-fetches cached URLs and existing transcription/segments from MongoDB, then passes them as Celery task kwargs. Worker receives everything it needs without DB access.

**Polling AsyncResult:**
```python
from celery.result import AsyncResult

result = AsyncResult(task_id, app=celery_app)
state = result.state       # "PENDING", "STARTED", "SUCCESS", "FAILURE"
if result.successful():
    data = result.get()    # dict returned by the task
elif result.failed():
    error = str(result.result)
```

**`persist_job_result()` — idempotent DB write on SUCCESS:**
- Called from `GET /jobs/{task_id}/status` polling, not from the worker.
- Uses MongoDB `$set` + conditional `$push` to prevent duplicate `dubbed_versions` entries keyed on `job_id`.
- Safe to call multiple times (repeated polling won't duplicate data).

```python
async def persist_job_result(task_id: str, result: dict) -> None:
    await videos_repo.update_video_after_dub(
        video_id=result["video_id"],
        job_id=task_id,
        dubbed_url=result["dubbed_url"],
        ...
    )
```

## Redis (Job Registration for WebSocket)

Register each job in Redis immediately after enqueueing so the WebSocket progress endpoint can stream updates:
```python
from app.services.jobs import register_job

await register_job(task_id, project_id=project_id, video_id=video_id)
```

The worker publishes progress to `job:{task_id}` pub/sub channel and stores latest state at `job:{task_id}:latest` (1h TTL via `SETEX`) so late-connecting WebSocket clients receive current state immediately.
