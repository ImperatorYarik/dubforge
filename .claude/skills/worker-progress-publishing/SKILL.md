---
name: worker-progress-publishing
description: This skill should be used when adding progress reporting to a pipeline step, publishing job progress to Redis, designing step names and percentage ranges, or ensuring WebSocket clients receive current state on late connection.
version: 1.0.0
---

# Worker Progress Publishing

## Why Two Redis Operations per Update

1. **Pub/Sub publish** (`PUBLISH job:{task_id} ...`) — streams to all currently connected WebSocket clients.
2. **SETEX latest state** (`SETEX job:{task_id}:latest <payload> EX 3600`) — stores current state so clients that connect *after* a step started still receive the latest progress immediately.

Both are mandatory for every progress update.

## Message Schema

```json
{
  "step": "transcribing",
  "pct": 45,
  "message": "Transcribing audio with Whisper..."
}
```

- `step`: short snake_case identifier for the pipeline stage.
- `pct`: integer 0–100.
- `message`: human-readable description shown in the UI.

## `progress_publisher` Service

Progress publishing is encapsulated in `services/progress_publisher.py`. Always use it — never inline Redis calls in tasks or pipelines:

```python
from app.services.progress_publisher import ProgressPublisher

publisher = ProgressPublisher(redis_client, task_id=job_id)
publisher.publish(step="separating_vocals", pct=10, message="Separating vocals with Demucs...")
```

## Percentage Ranges Per Pipeline Step

Divide the 0–100 range across steps so users see smooth progress:

| Step | Approx pct range |
|---|---|
| Downloading video | 0–5 |
| Separating vocals (Demucs) | 5–20 |
| Transcribing (Whisper) | 20–40 |
| Synthesising speech (XTTS) | 40–70 |
| Mixing audio (ffmpeg) | 70–90 |
| Uploading results | 90–99 |
| Complete | 100 |

Adjust ranges when adding new steps — keep them proportional to expected wall-clock time.

## Adding Progress to a New Step

Every new significant pipeline step MUST:
1. Publish at the start of the step with the starting `pct`.
2. Optionally publish mid-step for long-running operations (e.g. per-segment TTS).
3. Publish at completion before moving to the next step.

```python
publisher.publish(step="enhancing_audio", pct=72, message="Applying noise reduction...")
# ... do work ...
publisher.publish(step="enhancing_audio", pct=78, message="Noise reduction complete.")
```

## Terminal States

Always publish a final state so the WebSocket client knows the job is done:
```python
# On success
publisher.publish(step="complete", pct=100, message="Dubbing complete!")

# On failure (in the except block)
publisher.publish(step="failed", pct=0, message=f"Job failed: {str(exc)}")
```
