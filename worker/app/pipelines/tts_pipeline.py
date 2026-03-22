import os
import uuid
import json
import logging
import subprocess

import redis as sync_redis

from app.config import settings
from app.celery_app import celery
from app.tasks.tts import synthesize_builtin, release_model as release_tts
from app.tasks.transcribe import release_model as release_whisper
from app.tasks.upload import upload_to_s3

logger = logging.getLogger(__name__)

_redis = sync_redis.from_url(settings.REDIS_URL)


def _publish_progress(task_id: str, step: str, pct: int, message: str = ""):
    payload = json.dumps({"step": step, "pct": pct, "message": message})
    _redis.publish(f"job:{task_id}", payload)
    _redis.setex(f"job:{task_id}:latest", 3600, payload)


@celery.task(bind=True, max_retries=0, name="app.pipelines.tts_pipeline.generate_tts")
def generate_tts(self, text: str, speaker_name: str, output_format: str = "wav"):
    job_id = str(uuid.uuid4())
    tmp = f"/tmp/tts_{job_id}"
    os.makedirs(tmp, exist_ok=True)
    logger.info(f"[tts:{job_id}] speaker={speaker_name} format={output_format}")

    try:
        _publish_progress(self.request.id, "tts", 5, "Starting TTS synthesis")

        wav_path = f"{tmp}/output.wav"
        _publish_progress(self.request.id, "tts", 10, "Freeing Whisper from VRAM")
        release_whisper()
        _publish_progress(self.request.id, "tts", 15, "Loading TTS model")

        if not synthesize_builtin(text, wav_path, speaker_name):
            raise RuntimeError("TTS synthesis failed")

        _publish_progress(self.request.id, "tts", 80, "Synthesis complete")

        if output_format == "mp3":
            mp3_path = f"{tmp}/output.mp3"
            subprocess.run(
                ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-qscale:a", "2", mp3_path],
                check=True,
                capture_output=True,
            )
            final_path = mp3_path
        else:
            final_path = wav_path

        _publish_progress(self.request.id, "tts", 90, "Uploading audio")
        object_key = f"tts/{job_id}.{output_format}"
        audio_url = upload_to_s3(final_path, object_key)

        release_tts()
        _publish_progress(self.request.id, "tts", 100, "Done")
        logger.info(f"[tts:{job_id}] Done → {audio_url}")
        return {"audio_url": audio_url, "format": output_format}

    except Exception as exc:
        logger.error(f"[tts:{job_id}] Failed: {exc}")
        release_whisper()
        release_tts()
        raise exc
