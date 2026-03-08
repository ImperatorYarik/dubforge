from fastapi import APIRouter
from app.utils.queue import celery
from app.CRUD import videos
router = APIRouter()


@router.post("/dub")
async def dub_video(project_id: str, video_id: str):
    video = await videos.get_video(video_id)
    if not video:
        return {"error": "Video not found"}
    task = celery.send_task(
        "app.tasks.dub_pipeline.dub_video",
        args=[project_id, video_id, video["video_url"]],
    )
    return {"task_id": task.id, "status": "submitted"}