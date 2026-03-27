from typing import Optional

from pydantic import BaseModel


class JobContext(BaseModel):
    project_id: str
    video_id: str
    input_url: str
    job_id: str
    tmp_dir: str


class DubJobResult(BaseModel):
    status: str
    dubbed_url: str
    transcript_url: str
    vocals_url: str
    no_vocals_url: str
    video_id: str
    job_id: str
    transcription: Optional[str] = None
    transcript_segments: Optional[list[dict]] = None
    detected_language: Optional[str] = None
    duration_seconds: Optional[float] = None


class TranscribeJobResult(BaseModel):
    status: str
    video_id: str
    transcript_url: str
    transcription: Optional[str] = None
    transcript_segments: Optional[list[dict]] = None
    detected_language: Optional[str] = None
    duration_seconds: Optional[float] = None


class TtsJobResult(BaseModel):
    audio_url: str
    format: str


class SeparateJobResult(BaseModel):
    status: str
    video_id: str
    vocals_url: str
    no_vocals_url: str
