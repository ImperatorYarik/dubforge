import logging

from app.models.audio import SeparationResult
from app.tasks.download import download_file_to_disk
from app.tasks.upload import upload_to_s3

logger = logging.getLogger(__name__)


class AudioRepository:
    def download_cached_separation(
        self, vocals_url: str | None, no_vocals_url: str | None, tmp_dir: str
    ) -> SeparationResult | None:
        if not vocals_url:
            return None

        vocals_path = f"{tmp_dir}/vocals.wav"
        no_vocals_path = f"{tmp_dir}/no_vocals.wav"

        if not download_file_to_disk(vocals_url, vocals_path):
            raise RuntimeError("Failed to download existing vocals")

        if no_vocals_url:
            download_file_to_disk(no_vocals_url, no_vocals_path)

        return SeparationResult(vocals_path=vocals_path, no_vocals_path=no_vocals_path)

    def save_separation(
        self,
        project_id: str,
        job_id: str,
        result: SeparationResult,
    ) -> tuple[str, str]:
        vocals_url = upload_to_s3(result.vocals_path, f"{project_id}/vocals_{job_id}.wav")
        no_vocals_url = upload_to_s3(result.no_vocals_path, f"{project_id}/no_vocals_{job_id}.wav")
        return vocals_url, no_vocals_url


audio_repository = AudioRepository()
