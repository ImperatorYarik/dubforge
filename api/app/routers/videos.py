from fastapi import APIRouter, UploadFile, File
from app.models.video import VideoUploadResponse
from app.utils.storage import storage

router = APIRouter()

@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(file: UploadFile = File(...)):
    
    bucket_name = file.filename.lower().split('.')[0] + '-bucket'
    object_name = 'video' + file.filename.split('.')[-1]
    storage.create_bucket(bucket_name)
    if storage.upload_file(file, bucket_name, object_name):
        return VideoUploadResponse(video_id="12345", message="Video uploaded successfully", upload_url=f"http://example.com/upload/{object_name}")
    else:
        return VideoUploadResponse(video_id="12345", message="Failed to upload video", upload_url="")