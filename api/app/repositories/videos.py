import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import AsyncSessionLocal
from app.models.video import Video


async def add_video(project_id: str, video_url: str) -> str:
    video_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        async with session.begin():
            row = Video(
                video_id=video_id,
                project_id=project_id,
                video_url=video_url,
                dubbed_versions=[],
            )
            session.add(row)
    return video_id


async def list_videos() -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Video).order_by(Video.created_at))
        rows = result.scalars().all()
    return [_to_video_dict(row) for row in rows]


async def get_video(video_id: str) -> dict | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Video).where(Video.video_id == video_id)
        )
        row = result.scalar_one_or_none()
    return _to_video_dict(row) if row else None


async def get_dubbed_version(video_id: str, job_id: str) -> dict | None:
    video = await get_video(video_id)
    if not video:
        return None
    for v in video.get("dubbed_versions") or []:
        if v["job_id"] == job_id:
            return v
    return None


async def update_video_after_dub(video_id: str, result: dict) -> None:
    """Persist dubbing job results. Idempotent."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            res = await session.execute(
                select(Video).where(Video.video_id == video_id)
            )
            row = res.scalar_one_or_none()
            if not row:
                return

            row.dubbed_url = result["dubbed_url"]
            row.vocals_url = result.get("vocals_url")
            row.no_vocals_url = result.get("no_vocals_url")
            row.transcript_url = result.get("transcript_url")
            row.transcription = result.get("transcription")
            row.transcript_segments = result.get("transcript_segments")
            row.updated_at = datetime.now(timezone.utc)
            if result.get("detected_language"):
                row.detected_language = result["detected_language"]
            if result.get("duration_seconds") is not None:
                row.duration_seconds = result["duration_seconds"]

            # Idempotent append: only add if this job_id is not already present
            existing = list(row.dubbed_versions or [])
            if not any(v["job_id"] == result["job_id"] for v in existing):
                existing.append({
                    "job_id": result["job_id"],
                    "url": result["dubbed_url"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                row.dubbed_versions = existing
            # flag_modified is required because SQLAlchemy does not detect
            # in-place mutations on JSONB lists by object identity
            flag_modified(row, "dubbed_versions")


async def update_video_after_transcribe(video_id: str, result: dict) -> None:
    """Persist transcription job results. Idempotent."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            res = await session.execute(
                select(Video).where(Video.video_id == video_id)
            )
            row = res.scalar_one_or_none()
            if not row:
                return

            row.transcript_url = result["transcript_url"]
            row.transcription = result.get("transcription")
            row.transcript_segments = result.get("transcript_segments")
            row.updated_at = datetime.now(timezone.utc)
            if result.get("detected_language"):
                row.detected_language = result["detected_language"]
            if result.get("duration_seconds") is not None:
                row.duration_seconds = result["duration_seconds"]


async def delete_dubbed_version(video_id: str, job_id: str) -> dict | None:
    """Remove a dubbed version entry and return the deleted version dict."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            res = await session.execute(
                select(Video).where(Video.video_id == video_id)
            )
            row = res.scalar_one_or_none()
            if not row:
                return None

            versions = list(row.dubbed_versions or [])
            target = next((v for v in versions if v["job_id"] == job_id), None)
            if not target:
                return None

            remaining = [v for v in versions if v["job_id"] != job_id]
            row.dubbed_versions = remaining
            row.dubbed_url = remaining[-1]["url"] if remaining else None
            row.updated_at = datetime.now(timezone.utc)
            flag_modified(row, "dubbed_versions")

    return target


def _to_video_dict(row: Video) -> dict:
    return {
        "video_id": row.video_id,
        "project_id": row.project_id,
        "video_url": row.video_url,
        "transcription": row.transcription,
        "transcript_segments": row.transcript_segments or [],
        "transcript_url": row.transcript_url,
        "dubbed_url": row.dubbed_url,
        "dubbed_versions": row.dubbed_versions or [],
        "vocals_url": row.vocals_url,
        "no_vocals_url": row.no_vocals_url,
        "detected_language": row.detected_language,
        "duration_seconds": row.duration_seconds,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
