import json

from fastapi import APIRouter
from celery.result import AsyncResult
from app.utils.queue import celery
from app.CRUD import videos
import asyncio
import redis.asyncio as aioredis
from fastapi import WebSocket, WebSocketDisconnect
from app.config import settings

router = APIRouter()


@router.post("/dub")
async def dub_video(project_id: str, video_id: str):
    video = await videos.get_video(video_id)
    if not video:
        return {"error": "Video not found"}
    task = celery.send_task(
        "app.pipelines.dubbing_pipeline.dub_video",
        args=[project_id, video_id, video["video_url"]],
    )
    return {"task_id": task.id, "status": "submitted"}


@router.get("/{task_id}/status")
async def get_job_status(task_id: str):
    result = AsyncResult(task_id, app=celery)
    if result.state == "SUCCESS":
        return {"status": "completed", "result": result.result}
    elif result.state == "FAILURE":
        return {"status": "failed", "error": str(result.result)}
    else:
        return {"status": result.state.lower()}

@router.post("/transcribe")
async def transcribe_video(project_id: str, video_id: str, translate: bool = False):
    video = await videos.get_video(video_id)
    if not video:
        return {"error": "Video not found"}
    task = celery.send_task(
        "app.tasks.dub_pipeline.transcribe_video",
        args=[project_id, video_id, video["video_url"], translate],
    )
    return {"task_id": task.id, "status": "submitted"}


@router.websocket("/{task_id}/progress")
async def job_progress_ws(websocket: WebSocket, task_id: str):
    await websocket.accept()
    r = aioredis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe(f"job:{task_id}")
    try:
        # Send the latest cached state immediately so clients that connect
        # after some events were published don't start stuck at 0%
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
        await r.aclose()