import json
from typing import Optional
from urllib.parse import urlparse

import redis.asyncio as aioredis
from celery.result import AsyncResult
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.core.celery import celery
from app.core.storage import storage
from app.repositories import videos as videos_repo
from app.services.jobs import enrich_result, persist_job_result, register_job


def _object_key_from_url(url: str) -> str:
    parsed = urlparse(url)
    parts = parsed.path.lstrip("/").split("/", 1)
    return parts[1] if len(parts) == 2 else ""

router = APIRouter()

VALID_MODELS = {"tiny", "base", "small", "medium", "large-v2", "large-v3"}

@router.post("/dub")
async def dub_video(
    project_id: str,
    video_id: str,
    skip_transcription: bool = False,
    ducking_enabled: bool = True,
    ducking_level: float = 0.3,
    atempo_min: float = 0.75,
    atempo_max: float = 1.5,
):
    video = await videos_repo.get_video(video_id)
    if not video:
        return {"error": "Video not found"}
    if not storage.object_exists(_object_key_from_url(video["video_url"])):
        return {"error": "Source video file not found in storage. Please re-upload the video."}
    ducking_level = max(0.0, min(1.0, ducking_level))
    atempo_min = max(0.5, min(0.95, atempo_min))
    atempo_max = max(1.05, min(2.0, atempo_max))
    task = celery.send_task(
        "app.pipelines.dubbing_pipeline.dub_video",
        args=[project_id, video_id, video["video_url"]],
        kwargs={
            "vocals_url": video.get("vocals_url"),
            "no_vocals_url": video.get("no_vocals_url"),
            "existing_transcription": video.get("transcription") if skip_transcription else None,
            "existing_segments": video.get("transcript_segments") if skip_transcription else None,
            "existing_detected_language": video.get("detected_language") if skip_transcription else None,
            "existing_duration_seconds": video.get("duration_seconds") if skip_transcription else None,
            "skip_transcription": skip_transcription,
            "ducking_enabled": ducking_enabled,
            "ducking_level": ducking_level,
            "atempo_min": atempo_min,
            "atempo_max": atempo_max,
        },
    )
    await register_job(task.id, "dub", project_id, video_id)
    return {"task_id": task.id, "status": "submitted"}


@router.post("/separate")
async def separate_audio(project_id: str, video_id: str):
    video = await videos_repo.get_video(video_id)
    if not video:
        return {"error": "Video not found"}
    if not storage.object_exists(_object_key_from_url(video["video_url"])):
        return {"error": "Source video file not found in storage. Please re-upload the video."}
    task = celery.send_task(
        "app.pipelines.demucs_pipeline.separate_audio",
        args=[project_id, video_id, video["video_url"]],
    )
    await register_job(task.id, "separate", project_id, video_id)
    return {"task_id": task.id, "status": "submitted"}


@router.post("/transcribe")
async def transcribe_video(
    project_id: str,
    video_id: str,
    translate: bool = True,
    model: str = "large-v3",
    skip_demucs: bool = False,
    language: Optional[str] = None,
):
    if model not in VALID_MODELS:
        return {"error": f"Invalid model '{model}'. Valid: {sorted(VALID_MODELS)}"}
    video = await videos_repo.get_video(video_id)
    if not video:
        return {"error": "Video not found"}
    if not storage.object_exists(_object_key_from_url(video["video_url"])):
        return {"error": "Source video file not found in storage. Please re-upload the video."}
    task = celery.send_task(
        "app.pipelines.transcribe_pipeline.transcribe_video",
        args=[project_id, video_id, video["video_url"]],
        kwargs={
            "vocals_url": video.get("vocals_url"),
            "no_vocals_url": video.get("no_vocals_url"),
            "translate": translate,
            "model": model,
            "skip_demucs": skip_demucs,
            "language": language,
        },
    )
    await register_job(task.id, "transcribe", project_id, video_id)
    return {"task_id": task.id, "status": "submitted"}


@router.get("/recent")
async def get_recent_jobs(limit: int = 20):
    """Return the most recent jobs with their current state and progress."""
    r = aioredis.from_url(settings.REDIS_URL)
    try:
        task_ids = await r.zrevrange("jobs:registry", 0, limit - 1)
        jobs = []
        for raw_id in task_ids:
            task_id = raw_id.decode() if isinstance(raw_id, bytes) else raw_id
            meta_raw = await r.get(f"job:{task_id}:meta")
            if not meta_raw:
                continue
            meta = json.loads(meta_raw)
            latest_raw = await r.get(f"job:{task_id}:latest")
            latest = json.loads(latest_raw) if latest_raw else {}
            result = AsyncResult(task_id, app=celery)
            jobs.append({
                **meta,
                "state": result.state,
                "pct": latest.get("pct", 0),
                "message": latest.get("message", ""),
            })
        return jobs
    finally:
        await r.aclose()


@router.get("/{task_id}/status")
async def get_job_status(task_id: str):
    result = AsyncResult(task_id, app=celery)
    if result.state == "SUCCESS":
        raw = result.result or {}
        await persist_job_result(raw)
        enriched = await enrich_result(raw)
        return {
            "task_id": task_id,
            "state": "SUCCESS",
            "status": "completed",
            "pct": 100,
            "step": "done",
            "message": "Completed",
            "result": enriched,
        }
    if result.state == "FAILURE":
        return {
            "task_id": task_id,
            "state": "FAILURE",
            "status": "failed",
            "pct": 0,
            "step": "error",
            "message": str(result.result),
            "error": str(result.result),
        }
    return {
        "task_id": task_id,
        "state": result.state,
        "status": result.state.lower(),
        "pct": 0,
        "step": "pending",
        "message": "",
    }


@router.websocket("/{task_id}/progress")
async def job_progress_ws(websocket: WebSocket, task_id: str):
    # TODO: add WebSocket authentication when auth is implemented
    await websocket.accept()
    r = aioredis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe(f"job:{task_id}")
    try:
        latest = await r.get(f"job:{task_id}:latest")
        if latest:
            data = json.loads(latest)
            await websocket.send_json(data)
            if data.get("pct") >= 100:
                return

        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = json.loads(message["data"])
            await websocket.send_json(data)
            if data.get("pct") >= 100:
                break
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"job:{task_id}")
        await pubsub.aclose()
        await r.aclose()
