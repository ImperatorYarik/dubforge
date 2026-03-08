import logging
from app.celery_app import celery
from app.storage import storage
from app.tasks.download import download_file_to_disk
from app.tasks.extract_audio import extract_audio
from app.tasks.transcribe import transcribe_audio

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=3)
def transcribe_video(self, job_id: str, input_url: str):
    logger.info(f"[{job_id}] Task started. Input: {input_url}")
    try:
        filename = input_url.split("/")[-1]
        base = filename.rsplit(".", 1)[0]
        video_path = f"/tmp/{job_id}/{filename}"
        audio_path = f"/tmp/{job_id}/{base}.wav"
        txt_path   = f"/tmp/{job_id}/{base}.txt"

        logger.info(f"[{job_id}] Downloading video to {video_path}")
        if not download_file_to_disk(input_url, video_path):
            raise RuntimeError("Failed to download video")
        logger.info(f"[{job_id}] Download complete")

        logger.info(f"[{job_id}] Extracting audio to {audio_path}")
        if not extract_audio(video_path, audio_path):
            raise RuntimeError("Failed to extract audio")
        logger.info(f"[{job_id}] Audio extraction complete")

        logger.info(f"[{job_id}] Transcribing audio")
        transcribe_audio(audio_path, txt_path)
        logger.info(f"[{job_id}] Transcription complete, output: {txt_path}")

        logger.info(f"[{job_id}] Uploading result to MinIO")
        with open(txt_path, "rb") as f:
            storage.upload_file(f, f"results/{base}.txt")
        logger.info(f"[{job_id}] Upload complete")

        logger.info(f"[{job_id}] Task finished successfully")
        return {"status": "completed", "job_id": job_id}

    except Exception as exc:
        logger.error(f"[{job_id}] Task failed: {exc}. Retrying in 10s (attempt {self.request.retries + 1}/{self.max_retries})")
        raise self.retry(exc=exc, countdown=10)

