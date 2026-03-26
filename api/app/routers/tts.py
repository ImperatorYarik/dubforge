from celery.result import AsyncResult
from fastapi import APIRouter

from app.core.celery import celery
from app.schemas.tts import TtsRequest
from app.services.jobs import rewrite_url
from app.services.tts import SPEAKERS, VALID_FORMATS

router = APIRouter()


@router.get("/voices")
async def list_voices():
    return SPEAKERS


@router.post("/generate")
async def generate_tts(req: TtsRequest):
    fmt = req.format if req.format in VALID_FORMATS else "wav"
    task = celery.send_task(
        "app.pipelines.tts_pipeline.generate_tts",
        args=[req.text, req.speaker, fmt],
    )
    return {"task_id": task.id, "status": "submitted"}


@router.get("/{task_id}/status")
async def get_tts_status(task_id: str):
    result = AsyncResult(task_id, app=celery)
    if result.state == "SUCCESS":
        res = dict(result.result)
        if "audio_url" in res:
            res["audio_url"] = rewrite_url(res["audio_url"])
        return {"status": "completed", "result": res}
    if result.state == "FAILURE":
        return {"status": "failed", "error": str(result.result)}
    return {"status": result.state.lower()}
