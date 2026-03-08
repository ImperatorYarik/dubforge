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
    video_id = await videos.add_video(project_id, video_url)
    object_name = project_id + f'/{video_id}.' + file.filename.split('.')[-1]


    video_url = f"{storage.get_base_url()}/{object_name}"
    if storage.upload_file(file, object_name):
        return VideoUploadResponse(project_id=project_id, message="Video uploaded successfully", upload_url=f"{storage.get_base_url()}/{object_name}")
    else:
        return VideoUploadResponse(project_id=project_id, message="Failed to upload video", upload_url=f"{storage.get_base_url()}/{object_name}")


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