from app.utils.database import videos_collection
import uuid
from datetime import datetime


async def add_video(project_id: str, video_url: str):
    video_id = str(uuid.uuid4())
    video_data = {
        "video_id": video_id,
        "project_id": project_id,
        "video_url": video_url,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    await videos_collection.insert_one(video_data)
    return video_id


def _to_video_dict(video: dict) -> dict:
    return {
        "video_id": video["video_id"],
        "project_id": video["project_id"],
        "video_url": video["video_url"],
        "transcription": video.get("transcription"),
        "transcript_segments": video.get("transcript_segments") or [],
        "transcript_url": video.get("transcript_url"),
        "dubbed_url": video.get("dubbed_url"),
        "vocals_url": video.get("vocals_url"),
        "no_vocals_url": video.get("no_vocals_url"),
        "detected_language": video.get("detected_language"),
        "duration_seconds": video.get("duration_seconds"),
        "created_at": video["created_at"],
        "updated_at": video["updated_at"],
    }


async def list_videos():
    videos = []
    async for video in videos_collection.find():
        videos.append(_to_video_dict(video))
    return videos


async def get_video(video_id: str):
    video = await videos_collection.find_one({"video_id": video_id})
    return _to_video_dict(video) if video else None
