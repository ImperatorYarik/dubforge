import os
import uuid
import logging
import subprocess

from app.celery_app import celery
from app.tasks.download import download_file_to_disk
from app.tasks.upload import upload_to_s3
from app.tasks.extract_audio import extract_audio
from app.tasks.translate import translate_audio, release_model as release_whisper
from app.tasks.tts import synthesize, DEFAULT_SPEAKER
from app.tasks.audio_mix import stretch_clip, build_dubbed_audio, mux_audio_into_video, get_duration

logger = logging.getLogger(__name__)
DUCK_VOLUME = 0.1   # 10% — original speech barely audible under TTS


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
        if not download_file_to_disk(input_url, src_path):
            raise RuntimeError("Download failed")

        # 2. Extract full audio
        logger.info(f"[dub:{job_id}] Extracting audio")
        if not extract_audio(src_path, audio_path):
            raise RuntimeError("Audio extraction failed")

        # 3. Translate — get timed English segments
        logger.info(f"[dub:{job_id}] Translating")
        segments = translate_audio(audio_path, output_path=f"{tmp}/transcription.txt")

        # Free Whisper VRAM before loading TTS model
        release_whisper()

        # 4. TTS + stretch each segment to its window duration
        for i, seg in enumerate(segments):
            window = seg["end"] - seg["start"]
            raw_tts = f"{tmp}/tts_raw_{i}.wav"
            stretched_tts = f"{tmp}/tts_{i}.wav"

            logger.info(f"[dub:{job_id}] TTS seg {i}: '{seg['text'][:50]}…'")
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
        if not build_dubbed_audio(audio_path, segments, dubbed_audio, duck_volume):
            raise RuntimeError("Audio mix failed")

        # 6. Mux new audio into original video (stream copy)
        logger.info(f"[dub:{job_id}] Muxing")
        if not mux_audio_into_video(src_path, dubbed_audio, dubbed_video):
            raise RuntimeError("Mux failed")

        # 7. Upload results to S3
        logger.info(f"[dub:{job_id}] Uploading results")
        dubbed_url = upload_to_s3(
            dubbed_video,
            f"{project_id}/dubbed_{job_id}.{ext}",
        )
        transcript_url = upload_to_s3(
            f"{tmp}/transcription.txt",
            f"{project_id}/transcription_{job_id}.txt",
        )

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

