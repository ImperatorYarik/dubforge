import os
import uuid
import logging
import json
from datetime import datetime
import redis as sync_redis
from app.config import settings

from app.celery_app import celery
from app.database import videos_collection
from app.tasks.download import download_file_to_disk
from app.tasks.upload import upload_to_s3
from app.tasks.extract_audio import separate_sources
from app.tasks.transcribe import transcribe_audio, release_model as release_whisper

logger = logging.getLogger(__name__)

_redis = sync_redis.from_url(settings.REDIS_URL)


def _publish_progress(task_id: str, step: str, pct: int, message: str = ""):
    payload = json.dumps({"step": step, "pct": pct, "message": message})
    _redis.publish(f"job:{task_id}", payload)
    _redis.setex(f"job:{task_id}:latest", 3600, payload)


@celery.task(bind=True, max_retries=2, name="app.pipelines.transcribe_pipeline.transcribe_video")
def transcribe_video(self, project_id: str, video_id: str, input_url: str, translate: bool = True):
    job_id = str(uuid.uuid4())
    tmp = f"/tmp/{job_id}"
    os.makedirs(tmp, exist_ok=True)
    logger.info(f"[transcribe:{job_id}] Starting. src={input_url}")

    try:
        video_doc = videos_collection.find_one({"video_id": video_id})

        if video_doc and video_doc.get("vocals_url"):
            # Audio already separated — skip demucs, download existing vocals
            vocals_path = f"{tmp}/vocals.wav"
            _publish_progress(self.request.id, "transcribe", 5, "Downloading extracted audio")
            if not download_file_to_disk(video_doc["vocals_url"], vocals_path):
                raise RuntimeError("Failed to download existing vocals")
            _publish_progress(self.request.id, "transcribe", 20, "Audio ready")
        else:
            # Full extraction: download source + demucs
            ext = input_url.split(".")[-1]
            src_path = f"{tmp}/source.{ext}"
            _publish_progress(self.request.id, "transcribe", 0, "Downloading video")
            if not download_file_to_disk(input_url, src_path):
                raise RuntimeError("Download failed")
            _publish_progress(self.request.id, "transcribe", 10, "Separating audio sources")
            vocals_path, no_vocals_path = separate_sources(src_path, tmp)
            _publish_progress(self.request.id, "transcribe", 18, "Uploading extracted audio")
            vocals_url = upload_to_s3(vocals_path, f"{project_id}/vocals_{job_id}.wav")
            no_vocals_url = upload_to_s3(no_vocals_path, f"{project_id}/no_vocals_{job_id}.wav")
            videos_collection.update_one(
                {"video_id": video_id},
                {"$set": {
                    "vocals_url": vocals_url,
                    "no_vocals_url": no_vocals_url,
                    "updated_at": datetime.now(),
                }},
            )
            _publish_progress(self.request.id, "transcribe", 20, "Audio extraction complete")

        # Transcribe
        _publish_progress(self.request.id, "transcribe", 25, "Starting transcription")
        segments = transcribe_audio(vocals_path, output_path=None, translate=translate)
        _publish_progress(self.request.id, "transcribe", 90, "Transcription complete")

        output_path = f"{tmp}/transcription.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            for seg in segments:
                f.write(f"[{seg['start']:.2f}s - {seg['end']:.2f}s] {seg['text']}\n")

        transcript_url = upload_to_s3(output_path, f"{project_id}/transcription_{job_id}.txt")
        with open(output_path, "r", encoding="utf-8") as f:
            transcription_text = f.read()

        videos_collection.update_one(
            {"video_id": video_id},
            {"$set": {
                "transcription": transcription_text,
                "transcript_url": transcript_url,
                "updated_at": datetime.now(),
            }},
        )

        _publish_progress(self.request.id, "transcribe", 100, "Done")
        logger.info(f"[transcribe:{job_id}] Done → {transcript_url}")
        return {
            "status": "completed",
            "video_id": video_id,
            "transcript_url": transcript_url,
        }

    except Exception as exc:
        logger.error(f"[transcribe:{job_id}] Failed: {exc}")
        release_whisper()
        raise self.retry(exc=exc, countdown=15)
