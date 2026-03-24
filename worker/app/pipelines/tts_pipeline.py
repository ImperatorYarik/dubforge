import uuid
import logging
import subprocess

import redis as sync_redis

from app.config import settings
from app.celery_app import celery
from app.models.job import TtsJobResult
from app.pipelines.base import BasePipeline
from app.services.model_manager import model_manager
from app.services.progress_publisher import ProgressPublisher
from app.tasks.tts import synthesize_builtin
from app.tasks.upload import upload_to_s3

logger = logging.getLogger(__name__)

_redis = sync_redis.from_url(settings.REDIS_URL)


class TtsPipeline(BasePipeline):
    abstract = True

    def execute(
        self,
        job_id: str,
        text: str,
        speaker_name: str,
        output_format: str,
        progress: ProgressPublisher,
    ) -> TtsJobResult:
        tmp_dir = self._make_tmp(f"tts_{job_id}")

        progress.update("tts", 10, "Freeing Whisper from VRAM")
        model_manager.release_whisper()

        progress.update("tts", 15, "Loading TTS model")
        if not synthesize_builtin(text, f"{tmp_dir}/output.wav", speaker_name):
            raise RuntimeError("TTS synthesis failed")

        progress.update("tts", 80, "Synthesis complete")

        if output_format == "mp3":
            final_path = f"{tmp_dir}/output.mp3"
            subprocess.run(
                ["ffmpeg", "-y", "-i", f"{tmp_dir}/output.wav",
                 "-codec:a", "libmp3lame", "-qscale:a", "2", final_path],
                check=True, capture_output=True,
            )
        else:
            final_path = f"{tmp_dir}/output.wav"

        progress.update("tts", 90, "Uploading audio")
        audio_url = upload_to_s3(final_path, f"tts/{job_id}.{output_format}")

        model_manager.release_tts()
        self._cleanup_tmp(f"tts_{job_id}")

        return TtsJobResult(audio_url=audio_url, format=output_format)


@celery.task(bind=True, max_retries=0, base=TtsPipeline, name="app.pipelines.tts_pipeline.generate_tts")
def generate_tts(self, text: str, speaker_name: str, output_format: str = "wav"):
    job_id = str(uuid.uuid4())
    logger.info(f"[tts:{job_id}] speaker={speaker_name} format={output_format}")
    progress = ProgressPublisher(_redis, self.request.id, settings.PROGRESS_TTL_SECONDS)
    progress.update("tts", 5, "Starting TTS synthesis")
    try:
        result = self.execute(job_id, text, speaker_name, output_format, progress)
        progress.update("tts", 100, "Done")
        logger.info(f"[tts:{job_id}] Done → {result.audio_url}")
        return result.model_dump()
    except Exception as exc:
        logger.error(f"[tts:{job_id}] Failed: {exc}")
        model_manager.release_all()
        raise exc
