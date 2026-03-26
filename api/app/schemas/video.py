from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class TranscriptSegmentSchema(BaseModel):
    start: float
    end: float
    text: str


class DubbedVersionSchema(BaseModel):
    job_id: str
    url: str
    created_at: datetime


class VideoUploadResponse(BaseModel):
    video_id: str
    project_id: str
    message: str
    upload_url: str


class VideoResponse(BaseModel):
    video_id: str
    project_id: str
    video_url: str
    transcription: Optional[str] = None
    transcript_segments: Optional[List[TranscriptSegmentSchema]] = None
    transcript_url: Optional[str] = None
    dubbed_url: Optional[str] = None
    dubbed_versions: Optional[List[DubbedVersionSchema]] = None
    vocals_url: Optional[str] = None
    no_vocals_url: Optional[str] = None
    detected_language: Optional[str] = None
    duration_seconds: Optional[float] = None
    created_at: datetime
    updated_at: datetime
