import uuid
from datetime import datetime
from typing import Optional

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


async def update_video_after_dub(video_id: str, result: dict) -> None:
    """Persist dubbing job results to MongoDB. Idempotent."""
    update_fields = {
        "dubbed_url": result["dubbed_url"],
        "vocals_url": result.get("vocals_url"),
        "no_vocals_url": result.get("no_vocals_url"),
        "transcript_url": result.get("transcript_url"),
        "transcription": result.get("transcription"),
        "transcript_segments": result.get("transcript_segments"),
        "updated_at": datetime.now(),
    }
    if result.get("detected_language"):
        update_fields["detected_language"] = result["detected_language"]
    if result.get("duration_seconds") is not None:
        update_fields["duration_seconds"] = result["duration_seconds"]

    await videos_collection.update_one(
        {"video_id": video_id},
        {"$set": update_fields},
    )
    # Add to dubbed_versions only if this job_id is not already present
    await videos_collection.update_one(
        {
            "video_id": video_id,
            "dubbed_versions": {"$not": {"$elemMatch": {"job_id": result["job_id"]}}},
        },
        {"$push": {"dubbed_versions": {
            "job_id": result["job_id"],
            "url": result["dubbed_url"],
            "created_at": datetime.now(),
        }}},
    )


async def update_video_after_transcribe(video_id: str, result: dict) -> None:
    """Persist transcription job results to MongoDB. Idempotent."""
    update_fields = {
        "transcript_url": result["transcript_url"],
        "transcription": result.get("transcription"),
        "transcript_segments": result.get("transcript_segments"),
        "updated_at": datetime.now(),
    }
    if result.get("detected_language"):
        update_fields["detected_language"] = result["detected_language"]
    if result.get("duration_seconds") is not None:
        update_fields["duration_seconds"] = result["duration_seconds"]

    await videos_collection.update_one(
        {"video_id": video_id},
        {"$set": update_fields},
    )


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
