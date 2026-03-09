import os
import uuid
import logging
import subprocess
from datetime import datetime
import json
import redis as sync_redis
from app.config import settings

from app.database import videos_collection
from app.celery_app import celery
from app.tasks.download import download_file_to_disk
from app.tasks.upload import upload_to_s3
from app.tasks.extract_audio import extract_audio
from app.tasks.transcribe import transcribe_audio, release_model as release_whisper
from app.tasks.tts import synthesize, DEFAULT_SPEAKER
from app.tasks.audio_mix import stretch_clip, build_dubbed_audio, mux_audio_into_video, get_duration

logger = logging.getLogger(__name__)
DUCK_VOLUME = 0.1   # 10% — original speech barely audible under TTS

_redis = sync_redis.from_url(settings.REDIS_URL)

def _publish_progress(task_id: str, step: str, pct: int, message: str = ""):
    payload = json.dumps({
        "step": step,
        "pct": pct,
        "message": message,
    })
    _redis.publish(f"job:{task_id}", payload)
    # Also store latest state so WebSocket clients that connect late can catch up
    _redis.setex(f"job:{task_id}:latest", 3600, payload)

@celery.task(bind=True, max_retries=2, name="app.tasks.dub_pipeline.dub_video")
def dub_video(self, project_id: str, video_id: str, input_url: str, remove_original_audio: bool = True):
    job_id = str(uuid.uuid4())
    tmp = f"/tmp/{job_id}" 
    os.makedirs(tmp, exist_ok=True)
    logger.info(f"[dub:{job_id}] Starting. src={input_url}")

    try:
        ext = input_url.split(".")[-1]
        src_path       = f"{tmp}/source.{ext}"
        audio_path     = f"{tmp}/audio.wav"
        dubbed_audio   = f"{tmp}/dubbed_audio.wav"
        dubbed_video   = f"{tmp}/dubbed.{ext}"

        # 1. Download
        logger.info(f"[dub:{job_id}] Downloading")
        _publish_progress(self.request.id, "video_dub", 0, "Starting download")
        if not download_file_to_disk(input_url, src_path):
            raise RuntimeError("Download failed")
        _publish_progress(self.request.id, "video_dub", 5, "Download complete")

        # 2. Extract full audio
        logger.info(f"[dub:{job_id}] Extracting audio")
        _publish_progress(self.request.id, "video_dub", 10, "Extracting audio")
        if not extract_audio(src_path, audio_path):
            raise RuntimeError("Audio extraction failed")
        _publish_progress(self.request.id, "video_dub", 20, "Audio extraction complete")

        # 3. Transcribe — get timed English segments
        logger.info(f"[dub:{job_id}] Transcribing")
        _publish_progress(self.request.id, "video_dub", 25, "Starting transcription")
        segments = transcribe_audio(audio_path, output_path=f"{tmp}/transcription.txt")
        _publish_progress(self.request.id, "video_dub", 50, "Transcription complete")

        output_path = f"{tmp}/transcription.txt"

        logger.info(f"Writing transcription to {output_path}...")

        with open(output_path, "w", encoding="utf-8") as f:
            for segment in segments:
                f.write(f"[{segment['start']:.2f}s - {segment['end']:.2f}s] {segment['text']}\n")

        # Free Whisper VRAM before loading TTS model
        release_whisper()

        # 4. TTS + stretch each segment to its window duration
        for i, seg in enumerate(segments):
            window = seg["end"] - seg["start"]
            raw_tts = f"{tmp}/tts_raw_{i}.wav"
            stretched_tts = f"{tmp}/tts_{i}.wav"

            logger.info(f"[dub:{job_id}] TTS seg {i}: '{seg['text'][:50]}…'")
            pct = 55 + int((i / len(segments)) * 25)
            _publish_progress(self.request.id, "video_dub", pct, f"TTS segment {i + 1}/{len(segments)}")
            if not synthesize(seg["text"], raw_tts, DEFAULT_SPEAKER):
                logger.warning(f"TTS failed for segment {i}, using silence")
                # Create silence of correct duration as fallback
                subprocess.run([
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"anullsrc=r=22050:cl=mono:d={window}",
                    stretched_tts
                ], check=True, capture_output=True)
            else:
                if not stretch_clip(raw_tts, stretched_tts, window):
                    raise RuntimeError(f"Stretch failed for segment {i}")

            seg["tts_wav"] = stretched_tts

        # 5. Build final audio: duck original + overlay TTS clips
        duck_volume = 0.0 if remove_original_audio else DUCK_VOLUME
        logger.info(f"[dub:{job_id}] Mixing audio (remove_original={remove_original_audio}, duck={duck_volume})")
        _publish_progress(self.request.id, "video_dub", 80, "Mixing audio")
        if not build_dubbed_audio(audio_path, segments, dubbed_audio, duck_volume):
            raise RuntimeError("Audio mix failed")

        # 6. Mux new audio into original video (stream copy)
        logger.info(f"[dub:{job_id}] Muxing")
        _publish_progress(self.request.id, "video_dub", 90, "Muxing video")
        if not mux_audio_into_video(src_path, dubbed_audio, dubbed_video):
            raise RuntimeError("Mux failed")

        # 7. Upload results to S3
        logger.info(f"[dub:{job_id}] Uploading results")
        _publish_progress(self.request.id, "video_dub", 95, "Uploading results")
        dubbed_url = upload_to_s3(
            dubbed_video,
            f"{project_id}/dubbed_{job_id}.{ext}",
        )
        transcript_url = upload_to_s3(
            f"{tmp}/transcription.txt",
            f"{project_id}/transcription_{job_id}.txt",
        )
        _publish_progress(self.request.id, "video_dub", 100, "Uploading done")

        logger.info(f"[dub:{job_id}] Done → {dubbed_url}")
        return {
            "status": "completed",
            "dubbed_url": dubbed_url,
            "transcript_url": transcript_url,
            "video_id": video_id,
        }
    

    except Exception as exc:
        logger.error(f"[dub:{job_id}] Failed: {exc}")
        raise self.retry(exc=exc, countdown=15)



@celery.task(bind=True, max_retries=2, name="app.tasks.dub_pipeline.transcribe_video")
def transcribe_video(self, project_id: str, video_id: str, input_url: str, translate: bool = False):
    job_id = str(uuid.uuid4())
    tmp = f"/tmp/{job_id}"
    ext = input_url.split(".")[-1]
    src_path   = f"{tmp}/source.{ext}"
    audio_path = f"{tmp}/audio.wav"
    _publish_progress(self.request.id, "video_transcription", 0, "Downloading video")

    os.makedirs(tmp, exist_ok=True)
    logger.info(f"[transcribe:{job_id}] Starting. src={input_url}")
    # 1. Download
    logger.info(f"[transcribe:{job_id}] Downloading")
    if not download_file_to_disk(input_url, src_path):
        raise RuntimeError("Download failed")
    _publish_progress(self.request.id, "video_transcription", 10, "Extracting audio")

    logger.info(f"[transcribe:{job_id}] Extracting audio")
    if not extract_audio(src_path, audio_path):
        raise RuntimeError("Audio extraction failed")
    _publish_progress(self.request.id, "video_transcription", 20, "Audio extracted, transcribing…")

    logger.info(f"[transcribe:{job_id}] Transcribing")

    segments = transcribe_audio(audio_path, output_path=f"{tmp}/transcription.txt", translate=translate)
    _publish_progress(self.request.id, "video_transcription", 80, "Transcription complete")
    output_path = f"{tmp}/transcription.txt"

    logger.info(f"Writing transcription to {output_path}...")

    with open(output_path, "w", encoding="utf-8") as f:
        for segment in segments:
            f.write(f"[{segment['start']:.2f}s - {segment['end']:.2f}s] {segment['text']}\n")

    transcript_url = upload_to_s3(
            f"{tmp}/transcription.txt",
            f"{project_id}/transcription_{job_id}.txt",
        )

    transcription_text = "".join(seg["text"] for seg in segments)

    videos_collection.update_one(
        {"video_id": video_id},
        {"$set": {
            "transcription": transcription_text,
            "transcript_url": transcript_url,
            "updated_at": datetime.utcnow(),
        }},
    )
    logger.info(f"[transcribe:{job_id}] MongoDB updated for video_id={video_id}")

    _publish_progress(self.request.id, "video_transcription", 100, "Transcription done")

    # Free Whisper VRAM before loading TTS model
    release_whisper()
