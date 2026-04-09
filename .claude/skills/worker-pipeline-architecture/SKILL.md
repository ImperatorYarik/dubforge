---
name: worker-pipeline-architecture
description: This skill should be used when designing new pipeline tasks, deciding where code belongs (pipeline vs task vs service vs model), structuring Pydantic models for inter-task data, or reviewing worker code for single-responsibility violations.
version: 1.0.0
---

# Worker Pipeline Architecture

## Directory Layout

```
worker/app/
  celery_app.py          # Celery instance + Whisper pre-load at startup
  config.py              # pydantic-settings config (model names, thresholds, URLs)
  storage.py             # MinIO client singleton
  models/                # Pydantic data models (AudioData, JobData, ProgressEvent, Segment)
  services/              # Infrastructure services
  pipelines/             # Celery @task orchestrators
  tasks/                 # Atomic processing units
```

## Layer Responsibilities

### `pipelines/` — Orchestration Only
Pipelines are Celery `@task` functions that call tasks in sequence, pass data between them, publish progress, and handle top-level error/retry logic. They contain **no processing logic**.

```python
@celery.task(bind=True)
def dub_video(self, *, video_url, vocals_url, segments, job_id, ...):
    publisher = ProgressPublisher(redis, job_id)
    
    publisher.publish(step="downloading", pct=0, message="Downloading video...")
    video_path = download_video(video_url, job_id)
    
    publisher.publish(step="separating_vocals", pct=5, message="Separating vocals...")
    vocals_path, no_vocals_path = extract_audio(video_path, job_id)
    
    # ... etc
    return result_dict
```

### `tasks/` — Atomic Processing Units
Each task module has **one public function** that does exactly one thing:

| Module | What it does |
|---|---|
| `download.py` | Download a file from MinIO to local disk |
| `extract_audio.py` | ffmpeg audio extraction + Demucs vocal separation |
| `reference_audio.py` | Build voice reference WAV for XTTS |
| `transcribe.py` | Run Whisper on vocals, return segments |
| `tts.py` | XTTS v2 synthesis for a list of segments |
| `audio_mix.py` | ffmpeg atempo stretch + duck + overlay + video mux |
| `upload.py` | Upload result files to MinIO, return URLs |

Rules for task modules:
- Single public function with a clear, typed signature.
- ≤60 lines per function — extract helpers for anything longer.
- Use `pathlib.Path` for all file paths — never raw strings.
- No orchestration logic (no calls to other tasks, no progress publishing).

### `services/` — Infrastructure Concerns
Services abstract infrastructure so tasks stay clean:

| Service | Responsibility |
|---|---|
| `model_manager.py` | Load/release Whisper and XTTS models |
| `audio_repository.py` | Audio file I/O with MinIO |
| `transcript_repository.py` | Transcript storage (MinIO) |
| `progress_publisher.py` | Redis pub/sub + SETEX progress updates |

**Rule**: If a task needs to talk to MinIO, Redis, or manage a model — it calls a service, not the raw client.

### `models/` — Structured Inter-Task Data
Use Pydantic models for all data passed between tasks — never raw dicts:

```python
from app.models.segment import Segment
from app.models.audio import AudioData

segments: list[Segment] = transcribe(vocals_path)
audio: AudioData = synthesise_tts(segments, reference_wav)
```

### `config.py` — All Configurable Values
Model names, thresholds, and tunable parameters go in `config.py` (pydantic-settings). Never hardcode in tasks:

```python
# config.py
class WorkerSettings(BaseSettings):
    WHISPER_MODEL: str = "large-v3"
    DEMUCS_MODEL: str = "htdemucs"
    ATEMPO_MIN: float = 0.75
    ATEMPO_MAX: float = 1.50
    REFERENCE_AUDIO_MIN_SECONDS: float = 8.0
```

## Design Checklist for New Steps

When adding a new pipeline step:
1. **Which layer?** Processing logic → `tasks/`. Infrastructure I/O → `services/`. Orchestration → `pipelines/`.
2. **New Pydantic model needed?** If passing structured data between tasks, add to `models/`.
3. **Config values?** Model names, thresholds → `config.py`.
4. **VRAM impact?** If loading a GPU model, define load/release in `model_manager.py`.
5. **Progress events?** Add to the pipeline's publish sequence.
6. **MinIO caching?** If the step is expensive and deterministic, add a cache-check before running.
