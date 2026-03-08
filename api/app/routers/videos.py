from fastapi import APIRouter, UploadFile, File
from app.models.video import VideoUploadResponse
from app.utils.storage import storage


router = APIRouter()

@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(file: UploadFile = File(...), project_id: str = "default_folder"):
    object_name = project_id + '/video.' + file.filename.split('.')[-1]
    if storage.upload_file(file, object_name):
        return VideoUploadResponse(project_id=project_id, message="Video uploaded successfully", upload_url=f"{storage.get_base_url()}/{object_name}")
    else:
        return VideoUploadResponse(project_id=project_id, message="Failed to upload video", upload_url=f"{storage.get_base_url()}/{object_name}")