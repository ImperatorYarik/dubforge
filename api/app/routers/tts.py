from urllib.parse import urlparse

from fastapi import APIRouter
from pydantic import BaseModel
from celery.result import AsyncResult

from app.utils.queue import celery
from app.utils.storage import storage
from app.config import settings

router = APIRouter()

SPEAKERS = [
    {"name": "Claribel Dervla",  "gender": "F"},
    {"name": "Daisy Studious",   "gender": "F"},
    {"name": "Gracie Wise",      "gender": "F"},
    {"name": "Tammie Ema",       "gender": "F"},
    {"name": "Alison Dietlinde", "gender": "F"},
    {"name": "Ana Florence",     "gender": "F"},
    {"name": "Annmarie Nele",    "gender": "F"},
    {"name": "Asya Anara",       "gender": "F"},
    {"name": "Brenda Borne",     "gender": "F"},
    {"name": "Eldora Nonaka",    "gender": "F"},
    {"name": "Lone Sunness",     "gender": "F"},
    {"name": "Samantha Trice",   "gender": "F"},
    {"name": "Viktor Eka",       "gender": "F"},
    {"name": "Abrahan Mack",     "gender": "M"},
    {"name": "Andrew Chipper",   "gender": "M"},
    {"name": "Baldur Sanjin",    "gender": "M"},
    {"name": "Craig Gutsy",      "gender": "M"},
    {"name": "Damien Black",     "gender": "M"},
    {"name": "Ethan Flemming",   "gender": "M"},
    {"name": "Ferdie Sayers",    "gender": "M"},
]


@router.get("/voices")
async def list_voices():
    return SPEAKERS


class TtsRequest(BaseModel):
    text: str
    speaker: str
    format: str = "wav"


@router.post("/generate")
async def generate_tts(req: TtsRequest):
    fmt = req.format if req.format in ("wav", "mp3") else "wav"
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
            parsed = urlparse(res["audio_url"])
            parts = parsed.path.lstrip("/").split("/", 1)
            object_key = parts[1] if len(parts) == 2 else parsed.path.lstrip("/")
            internal_url = storage.generate_presigned_url(object_key, expires_in=3600)
            public_parsed = urlparse(settings.S3_PUBLIC_ENDPOINT)
            res["audio_url"] = urlparse(internal_url)._replace(
                scheme=public_parsed.scheme,
                netloc=public_parsed.netloc,
            ).geturl()
        return {"status": "completed", "result": res}
    elif result.state == "FAILURE":
        return {"status": "failed", "error": str(result.result)}
    else:
        return {"status": result.state.lower()}
