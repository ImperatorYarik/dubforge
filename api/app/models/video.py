from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class VideoUploadResponse(BaseModel):
    project_id: str
    message: str
    upload_url: str


class VideoResponse(BaseModel):
    video_id: str
    project_id: str
    video_url: str
    transcription: Optional[str] = None
    transcript_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
