from fastapi import APIRouter
from app.utils.queue import celery
from app.CRUD import videos
router = APIRouter()


@router.post("/transcribe")
async def transcribe_video(project_id: str, video_id: str):
    video = await videos.get_video(video_id)
    if not video:
        return {"error": "Video not found"}
    input_object = video["video_url"]
    task = celery.send_task(
        "app.tasks.pipeline.transcribe_video",
        args=[project_id, input_object],
    )
    return {"task_id": task.id, "status": "submitted"}