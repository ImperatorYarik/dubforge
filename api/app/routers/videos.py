from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from app.models.video import VideoUploadResponse, VideoResponse
from app.utils.storage import storage
from app.config import settings
from app.CRUD import videos


router = APIRouter()

@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(file: UploadFile = File(...), project_id: str = "default_folder"):
    import uuid as _uuid
    ext = file.filename.rsplit('.', 1)[-1] if file.filename and '.' in file.filename else 'mp4'
    object_name = f"{project_id}/{_uuid.uuid4()}.{ext}"
    video_url = f"{storage.get_base_url()}/{object_name}"
    if storage.upload_file(file, object_name):
        video_id = await videos.add_video(project_id, video_url)
        return VideoUploadResponse(video_id=video_id, project_id=project_id, message="Video uploaded successfully", upload_url=video_url)
    else:
        return VideoUploadResponse(video_id="", project_id=project_id, message="Failed to upload video", upload_url=video_url)


@router.get("/list_videos", response_model=list[VideoResponse])
async def list_videos():
    videos_list = await videos.list_videos()
    return videos_list


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: str):
    video = await videos.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.get("/{video_id}/dubbed-stream")
async def get_dubbed_stream_url(video_id: str):
    """Return a presigned URL for the dubbed video."""
    video = await videos.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not video.get("dubbed_url"):
        raise HTTPException(status_code=404, detail="No dubbed video available")

    parsed = urlparse(video["dubbed_url"])
    parts = parsed.path.lstrip("/").split("/", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=500, detail="Unexpected dubbed URL format")
    object_key = parts[1]

    internal_url = storage.generate_presigned_url(object_key, expires_in=3600)
    internal_parsed = urlparse(internal_url)
    public_parsed = urlparse(settings.S3_PUBLIC_ENDPOINT)
    public_url = internal_parsed._replace(
        scheme=public_parsed.scheme,
        netloc=public_parsed.netloc,
    ).geturl()

    return JSONResponse({"url": public_url})


@router.get("/{video_id}/vocals-stream")
async def get_vocals_stream_url(video_id: str):
    """Return a presigned URL for the vocals (voice-only) audio track."""
    video = await videos.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not video.get("vocals_url"):
        raise HTTPException(status_code=404, detail="No vocals track available — run Separate Audio first")

    parsed = urlparse(video["vocals_url"])
    parts = parsed.path.lstrip("/").split("/", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=500, detail="Unexpected vocals URL format")
    object_key = parts[1]

    internal_url = storage.generate_presigned_url(object_key, expires_in=3600)
    internal_parsed = urlparse(internal_url)
    public_parsed = urlparse(settings.S3_PUBLIC_ENDPOINT)
    public_url = internal_parsed._replace(
        scheme=public_parsed.scheme,
        netloc=public_parsed.netloc,
    ).geturl()

    return JSONResponse({"url": public_url})


@router.get("/{video_id}/no-vocals-stream")
async def get_no_vocals_stream_url(video_id: str):
    """Return a presigned URL for the no-vocals (background/music) audio track."""
    video = await videos.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not video.get("no_vocals_url"):
        raise HTTPException(status_code=404, detail="No background track available — run Separate Audio first")

    parsed = urlparse(video["no_vocals_url"])
    parts = parsed.path.lstrip("/").split("/", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=500, detail="Unexpected no_vocals URL format")
    object_key = parts[1]

    internal_url = storage.generate_presigned_url(object_key, expires_in=3600)
    internal_parsed = urlparse(internal_url)
    public_parsed = urlparse(settings.S3_PUBLIC_ENDPOINT)
    public_url = internal_parsed._replace(
        scheme=public_parsed.scheme,
        netloc=public_parsed.netloc,
    ).geturl()

    return JSONResponse({"url": public_url})


@router.get("/{video_id}/stream")
async def get_stream_url(video_id: str):
    """Return a short-lived presigned URL the browser can use to stream the video."""
    video = await videos.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Extract the S3 object key from the stored URL, e.g.
    # http://minio:9000/video-bucket/<project>/<file>  →  <project>/<file>
    parsed = urlparse(video["video_url"])
    # pathname is  /video-bucket/project/file  — strip leading /bucket-name/
    parts = parsed.path.lstrip("/").split("/", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=500, detail="Unexpected video URL format")
    object_key = parts[1]

    internal_url = storage.generate_presigned_url(object_key, expires_in=3600)

    # Rewrite the internal minio hostname to the public endpoint so the
    # browser can actually reach it.
    internal_parsed = urlparse(internal_url)
    public_parsed = urlparse(settings.S3_PUBLIC_ENDPOINT)
    public_url = internal_parsed._replace(
        scheme=public_parsed.scheme,
        netloc=public_parsed.netloc,
    ).geturl()

    return JSONResponse({"url": public_url})