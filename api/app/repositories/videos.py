import uuid
from datetime import datetime

from app.core.database import videos_collection


async def add_video(project_id: str, video_url: str) -> str:
    video_id = str(uuid.uuid4())
    await videos_collection.insert_one({
        "video_id": video_id,
        "project_id": project_id,
        "video_url": video_url,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    })
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
        "dubbed_versions": video.get("dubbed_versions") or [],
        "vocals_url": video.get("vocals_url"),
        "no_vocals_url": video.get("no_vocals_url"),
        "detected_language": video.get("detected_language"),
        "duration_seconds": video.get("duration_seconds"),
        "created_at": video["created_at"],
        "updated_at": video["updated_at"],
    }


async def list_videos() -> list[dict]:
    videos = []
    async for video in videos_collection.find():
        videos.append(_to_video_dict(video))
    return videos


async def get_video(video_id: str) -> dict | None:
    video = await videos_collection.find_one({"video_id": video_id})
    return _to_video_dict(video) if video else None


async def get_dubbed_version(video_id: str, job_id: str) -> dict | None:
    video = await videos_collection.find_one({"video_id": video_id})
    if not video:
        return None
    for v in video.get("dubbed_versions") or []:
        if v["job_id"] == job_id:
            return v
    return None


async def delete_dubbed_version(video_id: str, job_id: str) -> dict | None:
    """Remove a dubbed version entry and return the deleted version doc."""
    video = await videos_collection.find_one({"video_id": video_id})
    if not video:
        return None
    versions = video.get("dubbed_versions") or []
    target = next((v for v in versions if v["job_id"] == job_id), None)
    if not target:
        return None

    remaining = [v for v in versions if v["job_id"] != job_id]
    new_dubbed_url = remaining[-1]["url"] if remaining else None

    await videos_collection.update_one(
        {"video_id": video_id},
        {"$set": {
            "dubbed_versions": remaining,
            "dubbed_url": new_dubbed_url,
            "updated_at": datetime.now(),
        }},
    )
    return target
