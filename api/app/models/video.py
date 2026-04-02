from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Text, Float, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.project_id"), nullable=False, index=True
    )
    video_url: Mapped[str] = mapped_column(Text, nullable=False)
    transcription: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transcript_segments: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    transcript_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dubbed_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dubbed_versions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    vocals_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    no_vocals_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_language: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
