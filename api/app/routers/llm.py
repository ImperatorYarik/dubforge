import logging

import httpx
from celery.result import AsyncResult
from fastapi import APIRouter

from app.config import settings
from app.core.celery import celery
from app.repositories import videos as videos_repo

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/models")
async def get_models():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
        if response.status_code == 200:
            data = response.json()
            return {"models": [m["name"] for m in data.get("models", [])]}
        logger.warning(f"Ollama /api/tags returned {response.status_code}")
        return {"models": []}
    except Exception as e:
        logger.warning(f"Ollama unreachable: {e}")
        return {"models": []}


@router.post("/collect-context")
async def collect_context(
    project_id: str,
    video_id: str,
    model: str = None,
):
    video = await videos_repo.get_video(video_id)
    if not video:
        return {"error": "Video not found"}
    segments = video.get("transcript_segments") or []
    if not segments:
        return {"error": "No transcript segments found for this video"}
    if model is None:
        model = settings.OLLAMA_DEFAULT_MODEL
    task = celery.send_task(
        "app.tasks.collect_context.collect_transcription_context",
        kwargs={"segments": segments, "model": model},
    )
    return {"task_id": task.id, "status": "submitted"}


@router.get("/{task_id}/context-status")
async def get_context_status(task_id: str):
    result = AsyncResult(task_id, app=celery)
    if result.state == "SUCCESS":
        raw = result.result or {}
        return {"status": "completed", "context": raw.get("context", ""), "model": raw.get("model", "")}
    if result.state == "FAILURE":
        return {"status": "failed", "error": str(result.result)}
    return {"status": result.state.lower(), "task_id": task_id}


@router.post("/translate-segments")
async def translate_segments(payload: dict):
    segments = payload.get("segments", [])
    context = payload.get("context", "")
    model = payload.get("model") or settings.OLLAMA_DEFAULT_MODEL
    task = celery.send_task(
        "app.tasks.translate_segments.translate_segments_batch",
        kwargs={"segments": segments, "context": context, "model": model},
    )
    return {"task_id": task.id, "status": "submitted"}


@router.get("/{task_id}/translate-status")
async def get_translate_status(task_id: str):
    result = AsyncResult(task_id, app=celery)
    if result.state == "SUCCESS":
        raw = result.result or {}
        return {"status": "completed", "segments": raw.get("segments", [])}
    if result.state == "FAILURE":
        return {"status": "failed", "error": str(result.result)}
    return {"status": result.state.lower(), "task_id": task_id}
