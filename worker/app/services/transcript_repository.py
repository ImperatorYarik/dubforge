import re
import logging
from datetime import datetime
from typing import Optional

from app.database import videos_collection
from app.models.segment import TranscriptSegment
from app.tasks.upload import upload_to_s3

logger = logging.getLogger(__name__)

_SEGMENT_RE = re.compile(r"\[(\d+\.\d+)s - (\d+\.\d+)s\] (.+)")


class TranscriptRepository:
    def get_existing(
        self, video_id: str
    ) -> tuple[list[TranscriptSegment], str] | None:
        video_doc = videos_collection.find_one({"video_id": video_id})
        if not video_doc:
            return None

        # Prefer structured segments if available
        raw_segs = video_doc.get("transcript_segments")
        if raw_segs:
            segments = [
                TranscriptSegment(start=s["start"], end=s["end"], text=s["text"])
                for s in raw_segs
            ]
            text = video_doc.get("transcription", "")
            return (segments, text) if segments else None

        # Fall back to parsing plain text
        text = video_doc.get("transcription")
        if not text:
            return None

        segments = []
        for line in text.split("\n"):
            m = _SEGMENT_RE.match(line.strip())
            if m:
                segments.append(TranscriptSegment(
                    start=float(m.group(1)),
                    end=float(m.group(2)),
                    text=m.group(3),
                ))

        return (segments, text) if segments else None

    def save_transcription(
        self,
        video_id: str,
        project_id: str,
        job_id: str,
        segments: list[TranscriptSegment],
        tmp_dir: str,
        detected_language: Optional[str] = None,
        duration_seconds: Optional[float] = None,
    ) -> str:
        text = "".join(f"[{s.start:.2f}s - {s.end:.2f}s] {s.text}\n" for s in segments)
        output_path = f"{tmp_dir}/transcription.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)

        transcript_url = upload_to_s3(output_path, f"{project_id}/transcription_{job_id}.txt")

        update_fields = {
            "transcription": text,
            "transcript_url": transcript_url,
            "transcript_segments": [
                {"start": s.start, "end": s.end, "text": s.text}
                for s in segments
            ],
            "updated_at": datetime.now(),
        }
        if detected_language:
            update_fields["detected_language"] = detected_language
        if duration_seconds is not None:
            update_fields["duration_seconds"] = duration_seconds

        videos_collection.update_one(
            {"video_id": video_id},
            {"$set": update_fields},
        )
        return transcript_url


transcript_repository = TranscriptRepository()
