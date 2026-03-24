import re
import logging
from datetime import datetime

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
        if not (video_doc and video_doc.get("transcription")):
            return None

        text = video_doc["transcription"]
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
    ) -> str:
        text = "".join(f"[{s.start:.2f}s - {s.end:.2f}s] {s.text}\n" for s in segments)
        output_path = f"{tmp_dir}/transcription.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)

        transcript_url = upload_to_s3(output_path, f"{project_id}/transcription_{job_id}.txt")
        videos_collection.update_one(
            {"video_id": video_id},
            {"$set": {
                "transcription": text,
                "transcript_url": transcript_url,
                "updated_at": datetime.now(),
            }},
        )
        return transcript_url


transcript_repository = TranscriptRepository()
