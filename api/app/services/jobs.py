import json
import time
from typing import Optional
from urllib.parse import urlparse

import redis.asyncio as aioredis

from app.config import settings
from app.core.storage import storage
from app.repositories import videos as videos_repo


async def register_job(task_id: str, job_type: str, project_id: str, video_id: str) -> None:
    """Store job metadata in Redis registry for recent-jobs listing."""
    r = aioredis.from_url(settings.REDIS_URL)
    try:
        now = time.time()
        meta = json.dumps({
            "task_id": task_id,
            "type": job_type,
            "project_id": project_id,
            "video_id": video_id,
            "submitted_at": now,
        })
        await r.zadd("jobs:registry", {task_id: now})
        await r.set(f"job:{task_id}:meta", meta, ex=86400)
        # Keep registry tidy — trim to 100 entries
        await r.zremrangebyrank("jobs:registry", 0, -101)
    finally:
        await r.aclose()


def rewrite_url(internal_url: str) -> Optional[str]:
    """Generate a fresh presigned URL rewritten to the public endpoint."""
    if not internal_url:
        return None
    try:
        parsed = urlparse(internal_url)
        parts = parsed.path.lstrip("/").split("/", 1)
        object_key = parts[1] if len(parts) == 2 else parsed.path.lstrip("/")
        presigned = storage.generate_presigned_url(object_key, expires_in=3600)
        public_parsed = urlparse(settings.S3_PUBLIC_ENDPOINT)
        return urlparse(presigned)._replace(
            scheme=public_parsed.scheme,
            netloc=public_parsed.netloc,
        ).geturl()
    except Exception:
        return internal_url


async def persist_job_result(raw: dict) -> None:
    """Persist completed job results to MongoDB. Idempotent — safe to call multiple times."""
    video_id = raw.get("video_id")
    if not video_id:
        return  # TTS job — no video document to update

    if raw.get("dubbed_url"):
        await videos_repo.update_video_after_dub(video_id, raw)
    elif raw.get("transcript_url"):
        await videos_repo.update_video_after_transcribe(video_id, raw)


async def enrich_result(raw: dict) -> dict:
    """Rewrite S3 URLs to presigned public URLs and attach segment count."""
    enriched = dict(raw)

    for url_field in ("dubbed_url", "transcript_url", "vocals_url", "no_vocals_url", "audio_url"):
        if raw.get(url_field):
            enriched[url_field] = rewrite_url(raw[url_field])

    if raw.get("transcript_segments") is not None:
        enriched["segment_count"] = len(raw["transcript_segments"])

    return enriched
