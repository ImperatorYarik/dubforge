from pydantic import BaseModel
from datetime import datetime


class VideoUploadResponse(BaseModel):
    project_id: str
    message: str
    upload_url: str


class VideoResponse(BaseModel):
    video_id: str
    project_id: str
    video_url: str
    created_at: datetime
    updated_at: datetime
