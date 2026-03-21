import os
import uuid
import logging
import subprocess
from datetime import datetime
import json
import redis as sync_redis
from app.config import settings

from app.tasks.emotion import detect_emotion
from app.database import videos_collection
from app.celery_app import celery
from app.tasks.download import download_file_to_disk
from app.tasks.upload import upload_to_s3
from app.tasks.extract_audio import separate_sources
from app.tasks.transcribe import transcribe_audio, release_model as release_whisper
from app.tasks.tts import synthesize, release_model as release_tts
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

@celery.task(bind=True, max_retries=2, name="app.pipelines.dubbing_pipeline.dub_video")
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
        
        vocals_path, no_vocals_path = separate_sources(src_path, tmp)
        
        _publish_progress(self.request.id, "video_dub", 20, "Audio extraction complete")

        # 3. Transcribe — get timed English segments
        logger.info(f"[dub:{job_id}] Transcribing")
        _publish_progress(self.request.id, "video_dub", 25, "Starting transcription")
        segments = transcribe_audio(vocals_path, output_path=f"{tmp}/transcription.txt")
        _publish_progress(self.request.id, "video_dub", 50, "Transcription complete")

        output_path = f"{tmp}/transcription.txt"
        logger.info(f"Writing transcription to {output_path}...")

        with open(output_path, "w", encoding="utf-8") as f:
            for segment in segments:
                f.write(f"[{segment['start']:.2f}s - {segment['end']:.2f}s] {segment['text']}\n")

        # Extract speaker reference — longest clean segment — while Whisper is still loaded
        import soundfile as sf

        def _extract_reference(vocals_path: str, segments: list, output_path: str) -> tuple[str, str]:
            best = max(segments, key=lambda s: s["end"] - s["start"])
            audio, sr = sf.read(vocals_path)
            start, end = int(best["start"] * sr), int(best["end"] * sr)
            sf.write(output_path, audio[start:end], sr)
            return output_path, best["text"]

        reference_wav, reference_text = _extract_reference(vocals_path, segments, f"{tmp}/speaker_ref.wav")

        # Transcribe reference clip in original language so F5-TTS gets accurate ref_text
        # (doing this now while Whisper is still in VRAM)
        from app.tasks.transcribe import transcribe_audio as _transcribe
        ref_segs = _transcribe(reference_wav, output_path=None, translate=False)
        if ref_segs:
            reference_text = " ".join(s["text"] for s in ref_segs).strip()
        logger.info(f"Reference text for voice clone: '{reference_text[:80]}'")

        # Free Whisper VRAM before loading TTS / emotion models
        release_whisper()

        # Emotion detection on each segment to guide TTS style
        for i, seg in enumerate(segments):
            seg_wav = f"{tmp}/seg_{i}.wav"
            subprocess.run([
                "ffmpeg", "-y", "-i", vocals_path,
                "-ss", str(seg["start"]),
                "-to", str(seg["end"]),
                "-c", "copy",
                seg_wav
            ], check=True, capture_output=True)
            emotion, score = detect_emotion(seg_wav)
            seg["emotion"] = emotion
            seg["emotion_score"] = score
        
        # 4. TTS + stretch each segment to its window duration
        for i, seg in enumerate(segments):
            window = seg["end"] - seg["start"]
            raw_tts = f"{tmp}/tts_raw_{i}.wav"
            stretched_tts = f"{tmp}/tts_{i}.wav"

            logger.info(f"[dub:{job_id}] TTS seg {i}: '{seg['text'][:50]}…'")
            pct = 55 + int((i / len(segments)) * 25)
           
            _publish_progress(self.request.id, "video_dub", pct, f"TTS segment {i + 1}/{len(segments)}")
            
            if not synthesize(seg["text"], raw_tts, speaker=reference_wav, ref_text=reference_text, instruction=seg.get("emotion", "neutral")):
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

        # Free XTTS VRAM before mixing (no longer needed)
        release_tts()

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

        # Read transcription text to persist in DB so frontend can display it
        with open(f"{tmp}/transcription.txt", "r", encoding="utf-8") as _tf:
            transcription_text = _tf.read()

        # Persist dubbed_url so the frontend can recover it after a page reload
        videos_collection.update_one(
            {"video_id": video_id},
            {"$set": {
                "dubbed_url": dubbed_url,
                "transcript_url": transcript_url,
                "transcription": transcription_text,
                "updated_at": datetime.now(),
            }},
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
        release_tts()
        release_whisper()
        raise self.retry(exc=exc, countdown=15)


