from fastapi import APIRouter, UploadFile, File
from app.models.video import VideoUploadResponse
from app.utils.storage import storage


router = APIRouter()

@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(file: UploadFile = File(...), folder_name: str = "default_folder"):
    object_name = folder_name + '/video.' + file.filename.split('.')[-1]
    if storage.upload_file(file, object_name):
        return VideoUploadResponse(video_id="12345", message="Video uploaded successfully", upload_url=f"http://example.com/upload/{object_name}")
    else:
        return VideoUploadResponse(video_id="12345", message="Failed to upload video", upload_url="")
    
@router.post("/create-folder")
async def create_folder(folder_name: str):
    
    if storage.create_folder(folder_name):
        return {"message": f"Folder '{folder_name}' created successfully"}
    else:
        return {"message": f"Failed to create folder '{folder_name}'"}