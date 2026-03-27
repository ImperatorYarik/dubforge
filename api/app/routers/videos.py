import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.storage import storage
from app.repositories import videos as videos_repo
from app.schemas.video import VideoResponse, VideoUploadResponse

router = APIRouter()


def _object_key_from_url(url: str) -> str:
    parsed = urlparse(url)
    parts = parsed.path.lstrip("/").split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Unexpected URL format: {url}")
    return parts[1]


def _make_public_presigned(object_key: str) -> str:
    internal_url = storage.generate_presigned_url(object_key, expires_in=3600)
    internal_parsed = urlparse(internal_url)
    public_parsed = urlparse(settings.S3_PUBLIC_ENDPOINT)
    return internal_parsed._replace(scheme=public_parsed.scheme, netloc=public_parsed.netloc).geturl()


router = APIRouter()


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(file: UploadFile = File(...), project_id: str = "default_folder"):
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "mp4"
    object_name = f"{project_id}/{uuid.uuid4()}.{ext}"
    video_url = f"{storage.get_base_url()}/{object_name}"
    if storage.upload_file(file, object_name):
        video_id = await videos_repo.add_video(project_id, video_url)
        return VideoUploadResponse(
            video_id=video_id,
            project_id=project_id,
            message="Video uploaded successfully",
            upload_url=video_url,
        )
    return VideoUploadResponse(
        video_id="",
        project_id=project_id,
        message="Failed to upload video",
        upload_url=video_url,
    )


@router.get("/list_videos", response_model=list[VideoResponse])
async def list_videos():
    return await videos_repo.list_videos()


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: str):
    video = await videos_repo.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.get("/{video_id}/stream")
async def get_stream_url(video_id: str):
    """Return a short-lived presigned URL the browser can use to stream the video."""
    video = await videos_repo.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    try:
        return JSONResponse({"url": _make_public_presigned(_object_key_from_url(video["video_url"]))})
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{video_id}/dubbed-stream")
async def get_dubbed_stream_url(video_id: str):
    """Return a presigned URL for the latest dubbed video."""
    video = await videos_repo.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not video.get("dubbed_url"):
        raise HTTPException(status_code=404, detail="No dubbed video available")
    try:
        return JSONResponse({"url": _make_public_presigned(_object_key_from_url(video["dubbed_url"]))})
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{video_id}/vocals-stream")
async def get_vocals_stream_url(video_id: str):
    """Return a presigned URL for the vocals (voice-only) audio track."""
    video = await videos_repo.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not video.get("vocals_url"):
        raise HTTPException(status_code=404, detail="No vocals track available — run Separate Audio first")
    try:
        return JSONResponse({"url": _make_public_presigned(_object_key_from_url(video["vocals_url"]))})
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{video_id}/no-vocals-stream")
async def get_no_vocals_stream_url(video_id: str):
    """Return a presigned URL for the no-vocals (background/music) audio track."""
    video = await videos_repo.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not video.get("no_vocals_url"):
        raise HTTPException(status_code=404, detail="No background track available — run Separate Audio first")
    try:
        return JSONResponse({"url": _make_public_presigned(_object_key_from_url(video["no_vocals_url"]))})
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{video_id}/dubbed-versions/{job_id}/stream")
async def get_dubbed_version_stream_url(video_id: str, job_id: str):
    """Return a presigned URL for a specific dubbed version by job_id."""
    version = await videos_repo.get_dubbed_version(video_id, job_id)
    if not version:
        raise HTTPException(status_code=404, detail="Dubbed version not found")
    try:
        return JSONResponse({"url": _make_public_presigned(_object_key_from_url(version["url"]))})
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{video_id}/dubbed-versions/{job_id}")
async def delete_dubbed_version(video_id: str, job_id: str):
    """Delete a dubbed version from MinIO and remove it from the video record."""
    deleted = await videos_repo.delete_dubbed_version(video_id, job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dubbed version not found")
    try:
        storage.delete_object(_object_key_from_url(deleted["url"]))
    except Exception:  # nosec B110 — best-effort MinIO deletion; DB record is already removed
        pass
    return JSONResponse({"deleted": job_id})
