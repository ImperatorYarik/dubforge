import logging
from datetime import datetime

from app.database import videos_collection
from app.models.audio import SeparationResult
from app.tasks.download import download_file_to_disk
from app.tasks.upload import upload_to_s3

logger = logging.getLogger(__name__)


class AudioRepository:
    def download_cached_separation(
        self, video_id: str, tmp_dir: str
    ) -> SeparationResult | None:
        video_doc = videos_collection.find_one({"video_id": video_id})
        if not (video_doc and video_doc.get("vocals_url")):
            return None

        vocals_path = f"{tmp_dir}/vocals.wav"
        no_vocals_path = f"{tmp_dir}/no_vocals.wav"

        if not download_file_to_disk(video_doc["vocals_url"], vocals_path):
            raise RuntimeError("Failed to download existing vocals")

        if video_doc.get("no_vocals_url"):
            download_file_to_disk(video_doc["no_vocals_url"], no_vocals_path)

        return SeparationResult(vocals_path=vocals_path, no_vocals_path=no_vocals_path)

    def save_separation(
        self,
        video_id: str,
        project_id: str,
        job_id: str,
        result: SeparationResult,
    ) -> tuple[str, str]:
        vocals_url = upload_to_s3(result.vocals_path, f"{project_id}/vocals_{job_id}.wav")
        no_vocals_url = upload_to_s3(result.no_vocals_path, f"{project_id}/no_vocals_{job_id}.wav")
        videos_collection.update_one(
            {"video_id": video_id},
            {"$set": {
                "vocals_url": vocals_url,
                "no_vocals_url": no_vocals_url,
                "updated_at": datetime.now(),
            }},
        )
        return vocals_url, no_vocals_url


audio_repository = AudioRepository()
