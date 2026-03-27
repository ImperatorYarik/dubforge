import re
import logging
from typing import Optional

from app.models.segment import TranscriptSegment
from app.tasks.upload import upload_to_s3

logger = logging.getLogger(__name__)

_SEGMENT_RE = re.compile(r"\[(\d+\.\d+)s - (\d+\.\d+)s\] (.+)")


class TranscriptRepository:
    @staticmethod
    def parse_existing(
        transcript_segments: list[dict] | None,
        transcription: str | None,
    ) -> tuple[list[TranscriptSegment], str] | None:
        """Parse transcription data passed in from the API (no DB access)."""
        if transcript_segments:
            segments = [
                TranscriptSegment(start=s["start"], end=s["end"], text=s["text"])
                for s in transcript_segments
            ]
            text = transcription or ""
            return (segments, text) if segments else None

        # Fall back to parsing plain text
        if not transcription:
            return None

        segments = []
        for line in transcription.split("\n"):
            m = _SEGMENT_RE.match(line.strip())
            if m:
                segments.append(TranscriptSegment(
                    start=float(m.group(1)),
                    end=float(m.group(2)),
                    text=m.group(3),
                ))

        return (segments, transcription) if segments else None

    def save_transcription(
        self,
        project_id: str,
        job_id: str,
        segments: list[TranscriptSegment],
        tmp_dir: str,
        detected_language: Optional[str] = None,
        duration_seconds: Optional[float] = None,
    ) -> str:
        """Write transcription file, upload to S3, and return the URL.
        DB persistence is the API's responsibility."""
        text = "".join(f"[{s.start:.2f}s - {s.end:.2f}s] {s.text}\n" for s in segments)
        output_path = f"{tmp_dir}/transcription.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)

        return upload_to_s3(output_path, f"{project_id}/transcription_{job_id}.txt")


transcript_repository = TranscriptRepository()
