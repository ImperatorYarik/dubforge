---
name: worker-minio-storage
description: This skill should be used when writing worker code that uploads or downloads files to/from MinIO, designing object key names for new artifact types, implementing the MinIO-based caching pattern for expensive AI steps, or ensuring no local filesystem state persists across tasks.
version: 1.0.0
---

# Worker MinIO Storage

## Golden Rule: No Local Filesystem Persistence Across Task Boundaries

Workers use local disk only as temporary scratch space during a single task execution. All intermediate and output files MUST be uploaded to MinIO before the task ends. Local temp files are deleted after upload.

```python
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmpdir:
    local_path = Path(tmpdir) / "vocals.wav"
    # ... write to local_path ...
    vocals_url = storage.upload_file(local_path, bucket, key)
# tmpdir and all contents are deleted here
```

## Object Key Naming Convention

```
{bucket}/
  {project_id}/video.mp4                      # original upload
  {project_id}/vocals_{job_id}.wav            # Demucs vocals (cached)
  {project_id}/no_vocals_{job_id}.wav         # Demucs background (cached)
  {project_id}/transcription_{job_id}.txt     # transcription text
  {project_id}/dubbed_{job_id}.mp4            # dubbed output video
  tts/{job_id}.wav                            # standalone TTS output
```

Pattern: `{project_id}/{artifact_type}_{job_id}.{ext}`

For new artifact types, follow this pattern exactly:
```python
key = f"{project_id}/{artifact_type}_{job_id}.{ext}"
# e.g. f"{project_id}/enhanced_audio_{job_id}.wav"
```

## Caching Pattern for Expensive Steps

Before running an expensive, deterministic AI step, check if the result already exists in MinIO:

```python
async def get_or_compute_vocals(project_id: str, job_id: str, video_path: Path) -> tuple[str, str]:
    """Return cached vocal URLs if available, otherwise run Demucs."""
    vocals_key = f"{project_id}/vocals_{job_id}.wav"
    no_vocals_key = f"{project_id}/no_vocals_{job_id}.wav"
    
    if storage.object_exists(bucket, vocals_key) and storage.object_exists(bucket, no_vocals_key):
        return storage.get_url(bucket, vocals_key), storage.get_url(bucket, no_vocals_key)
    
    vocals_path, no_vocals_path = run_demucs(video_path)
    vocals_url = storage.upload_file(vocals_path, bucket, vocals_key)
    no_vocals_url = storage.upload_file(no_vocals_path, bucket, no_vocals_key)
    return vocals_url, no_vocals_url
```

Apply this pattern to any step that:
- Takes >5 seconds to compute
- Produces deterministic output from the same input
- Could be re-used in a re-dub job

## Storage Service API (via `services/audio_repository.py`)

Never call `storage.py` directly from tasks — always go through the service layer:

```python
from app.services.audio_repository import AudioRepository

audio_repo = AudioRepository(storage_client)
vocals_url = await audio_repo.save_vocals(vocals_path, project_id=project_id, job_id=job_id)
vocals_path = await audio_repo.load_vocals(vocals_url, dest_dir=tmpdir)
```

## URL Format

Worker uploads use internal MinIO URLs (`http://minio:9000/...`). The API rewrites these to public URLs using `S3_PUBLIC_ENDPOINT` before returning them to the browser. The worker should never concern itself with URL rewriting — just return the raw MinIO URLs in the task result.
