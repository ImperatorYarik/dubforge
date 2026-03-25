from pydantic import BaseModel
from typing import Optional, List


class TranscriptSegmentResult(BaseModel):
    start: float
    end: float
    text: str


class JobResult(BaseModel):
    dubbed_url: Optional[str] = None
    transcript_url: Optional[str] = None
    transcription: Optional[str] = None
    transcript_segments: Optional[List[TranscriptSegmentResult]] = None
    detected_language: Optional[str] = None
    duration_seconds: Optional[float] = None
    segment_count: Optional[int] = None
    vocals_url: Optional[str] = None
    no_vocals_url: Optional[str] = None
    video_id: Optional[str] = None


class JobStatusResponse(BaseModel):
    task_id: str
    state: str
    status: str
    pct: int
    step: str
    message: str
    result: Optional[JobResult] = None
    error: Optional[str] = None
