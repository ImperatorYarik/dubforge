from pydantic import BaseModel

class VideoUploadResponse(BaseModel):
    video_id: str
    message: str
    upload_url: str