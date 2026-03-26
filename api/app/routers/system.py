import logging
import subprocess

import redis.asyncio as aioredis
from fastapi import APIRouter

from app.config import settings
from app.core.celery import celery

logger = logging.getLogger(__name__)
router = APIRouter()


def _gpu_info() -> dict:
    """Return GPU info via nvidia-smi. Falls back to zeros if unavailable."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            parts = [p.strip() for p in result.stdout.strip().split("\n")[0].split(",")]
            return {"available": True, "name": parts[0], "used_mb": int(parts[1]), "total_mb": int(parts[2])}
    except Exception as e:
        logger.debug(f"nvidia-smi unavailable: {e}")
    return {"available": False, "name": None, "used_mb": 0, "total_mb": 0}


@router.get("/status")
async def system_status():
    gpu = _gpu_info()

    r = aioredis.from_url(settings.REDIS_URL)
    try:
        whisper_loaded = await r.get("model:whisper:loaded") == b"1"
        xtts_loaded = await r.get("model:xtts:loaded") == b"1"
    except Exception:
        whisper_loaded = False
        xtts_loaded = False
    finally:
        await r.aclose()

    worker_online = False
    active_jobs = 0
    queued_jobs = 0
    try:
        inspect = celery.control.inspect(timeout=1.0)
        if inspect.ping():
            worker_online = True
            active_jobs = sum(len(v) for v in (inspect.active() or {}).values())
            queued_jobs = sum(len(v) for v in (inspect.reserved() or {}).values())
    except Exception as e:
        logger.debug(f"Celery inspect failed: {e}")

    return {
        "gpu_available": gpu["available"],
        "gpu_name": gpu["name"],
        "gpu_memory_used_mb": gpu["used_mb"],
        "gpu_memory_total_mb": gpu["total_mb"],
        "whisper_loaded": whisper_loaded,
        "xtts_loaded": xtts_loaded,
        "worker_online": worker_online,
        "active_jobs": active_jobs,
        "queued_jobs": queued_jobs,
    }
