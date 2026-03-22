import os
import re
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
from app.tasks.extract_audio import separate_sources
from app.tasks.transcribe import transcribe_audio, release_model as release_whisper
from app.tasks.tts import synthesize, release_model as release_tts
from app.tasks.audio_mix import stretch_clip, build_dubbed_audio, mux_audio_into_video, get_duration

logger = logging.getLogger(__name__)
DUCK_VOLUME = 0.1

_redis = sync_redis.from_url(settings.REDIS_URL)


def _publish_progress(task_id: str, step: str, pct: int, message: str = ""):
    payload = json.dumps({"step": step, "pct": pct, "message": message})
    _redis.publish(f"job:{task_id}", payload)
    _redis.setex(f"job:{task_id}:latest", 3600, payload)


def _parse_transcription(text: str) -> list:
    segments = []
    for line in text.split("\n"):
        m = re.match(r"\[(\d+\.\d+)s - (\d+\.\d+)s\] (.+)", line.strip())
        if m:
            segments.append({
                "start": float(m.group(1)),
                "end": float(m.group(2)),
                "text": m.group(3),
            })
    return segments


@celery.task(bind=True, max_retries=2, name="app.pipelines.dubbing_pipeline.dub_video")
def dub_video(self, project_id: str, video_id: str, input_url: str,
              remove_original_audio: bool = True, skip_transcription: bool = False):
    job_id = str(uuid.uuid4())
    tmp = f"/tmp/{job_id}"
    os.makedirs(tmp, exist_ok=True)
    logger.info(f"[dub:{job_id}] Starting. src={input_url} skip_transcription={skip_transcription}")

    try:
        ext = input_url.split(".")[-1]
        src_path     = f"{tmp}/source.{ext}"
        dubbed_audio = f"{tmp}/dubbed_audio.wav"
        dubbed_video = f"{tmp}/dubbed.{ext}"
        vocals_path    = f"{tmp}/vocals.wav"
        no_vocals_path = f"{tmp}/no_vocals.wav"

        # Always download source video (needed for mux)
        _publish_progress(self.request.id, "video_dub", 0, "Downloading source video…")
        if not download_file_to_disk(input_url, src_path):
            raise RuntimeError("Download failed")
        _publish_progress(self.request.id, "video_dub", 5, "Download complete")

        # 1. Audio extraction — skip if vocals already in DB
        video_doc = videos_collection.find_one({"video_id": video_id})

        if video_doc and video_doc.get("vocals_url"):
            logger.info(f"[dub:{job_id}] Reusing existing vocals from DB")
            _publish_progress(self.request.id, "video_dub", 8, "Downloading previously extracted audio…")
            if not download_file_to_disk(video_doc["vocals_url"], vocals_path):
                raise RuntimeError("Failed to download existing vocals")
            if video_doc.get("no_vocals_url"):
                download_file_to_disk(video_doc["no_vocals_url"], no_vocals_path)
            _publish_progress(self.request.id, "video_dub", 15, "Audio ready")
        else:
            logger.info(f"[dub:{job_id}] Separating audio sources")
            _publish_progress(self.request.id, "video_dub", 10, "Separating vocals from background (Demucs)…")
            v, nv = separate_sources(src_path, tmp)
            vocals_path = v
            no_vocals_path = nv
            _publish_progress(self.request.id, "video_dub", 18, "Uploading extracted audio…")
            vocals_url = upload_to_s3(vocals_path, f"{project_id}/vocals_{job_id}.wav")
            no_vocals_url = upload_to_s3(no_vocals_path, f"{project_id}/no_vocals_{job_id}.wav")
            videos_collection.update_one(
                {"video_id": video_id},
                {"$set": {"vocals_url": vocals_url, "no_vocals_url": no_vocals_url}},
            )
            _publish_progress(self.request.id, "video_dub", 20, "Audio extraction complete")

        # 2. Transcription — skip if requested and data exists in DB
        import numpy as np
        import soundfile as sf

        def _extract_reference_wav(v_path: str, segs: list, out: str, target_dur: float = 8.0):
            """Build voice reference by concatenating the longest segments until ≥target_dur seconds.
            Downmixes stereo to mono. Longer, cleaner reference = better XTTS voice cloning.
            """
            audio, sr = sf.read(v_path)
            if audio.ndim == 2:
                audio = audio.mean(axis=1)  # stereo → mono

            sorted_segs = sorted(segs, key=lambda s: s["end"] - s["start"], reverse=True)
            chunks = []
            total = 0.0
            for seg in sorted_segs:
                start = max(0, int(seg["start"] * sr))
                end = min(len(audio), int(seg["end"] * sr))
                chunk = audio[start:end]
                if len(chunk) > int(0.5 * sr):  # skip chunks < 0.5s
                    chunks.append(chunk)
                    total += len(chunk) / sr
                if total >= target_dur:
                    break

            if not chunks:
                raise RuntimeError("No usable audio segments for voice reference")

            ref_audio = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]
            sf.write(out, ref_audio, sr)
            logger.info(f"[ref] Built {total:.1f}s reference from {len(chunks)} segment(s)")
            return out, sorted_segs[0]["text"]

        if skip_transcription and video_doc and video_doc.get("transcription"):
            logger.info(f"[dub:{job_id}] Skipping transcription — using existing")
            _publish_progress(self.request.id, "video_dub", 22, "Loading existing transcription…")
            segments = _parse_transcription(video_doc["transcription"])
            if not segments:
                raise RuntimeError("No parseable segments in existing transcription")

            output_path = f"{tmp}/transcription.txt"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(video_doc["transcription"])

            reference_wav = f"{tmp}/speaker_ref.wav"
            reference_wav, reference_text = _extract_reference_wav(vocals_path, segments, reference_wav)

            release_whisper()
            _publish_progress(self.request.id, "video_dub", 50, "Transcription ready — loading TTS model…")

        else:
            logger.info(f"[dub:{job_id}] Transcribing")
            _publish_progress(self.request.id, "video_dub", 25, "Transcribing audio (Whisper)…")
            segments = transcribe_audio(vocals_path, output_path=f"{tmp}/transcription.txt")
            _publish_progress(self.request.id, "video_dub", 50, "Transcription complete — loading TTS model…")

            output_path = f"{tmp}/transcription.txt"
            with open(output_path, "w", encoding="utf-8") as f:
                for segment in segments:
                    f.write(f"[{segment['start']:.2f}s - {segment['end']:.2f}s] {segment['text']}\n")

            reference_wav, reference_text = _extract_reference_wav(
                vocals_path, segments, f"{tmp}/speaker_ref.wav"
            )

            logger.info(f"Reference text for voice clone: '{reference_text[:80]}'")
            release_whisper()

        # 3. TTS + stretch each segment
        _publish_progress(self.request.id, "video_dub", 53, "Synthesizing dubbed audio…")
        for i, seg in enumerate(segments):
            window = seg["end"] - seg["start"]
            raw_tts = f"{tmp}/tts_raw_{i}.wav"
            stretched_tts = f"{tmp}/tts_{i}.wav"

            pct = 55 + int((i / len(segments)) * 23)
            _publish_progress(self.request.id, "video_dub", pct, f"Synthesizing segment {i + 1}/{len(segments)}…")

            if not synthesize(seg["text"], raw_tts, speaker=reference_wav,
                              ref_text=reference_text):
                logger.warning(f"[dub:{job_id}] TTS failed for segment {i}, using silence")
                subprocess.run([
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"anullsrc=r=22050:cl=mono:d={window}",
                    stretched_tts
                ], check=True, capture_output=True)
            else:
                if not stretch_clip(raw_tts, stretched_tts, window):
                    raise RuntimeError(f"Stretch failed for segment {i}")

            seg["tts_wav"] = stretched_tts

        release_tts()

        # 5. Mix audio
        _publish_progress(self.request.id, "video_dub", 80, "Mixing dubbed audio with background…")
        if not build_dubbed_audio(no_vocals_path, segments, dubbed_audio, duck_volume=1.0):
            raise RuntimeError("Audio mix failed")

        # 6. Mux
        _publish_progress(self.request.id, "video_dub", 90, "Muxing audio into video…")
        if not mux_audio_into_video(src_path, dubbed_audio, dubbed_video):
            raise RuntimeError("Mux failed")

        # 7. Upload results
        _publish_progress(self.request.id, "video_dub", 95, "Uploading results…")
        dubbed_url = upload_to_s3(dubbed_video, f"{project_id}/dubbed_{job_id}.{ext}")
        transcript_url = upload_to_s3(output_path, f"{project_id}/transcription_{job_id}.txt")
        vocals_url_out = upload_to_s3(vocals_path, f"{project_id}/vocals_{job_id}.wav")
        no_vocals_url_out = upload_to_s3(no_vocals_path, f"{project_id}/no_vocals_{job_id}.wav")

        with open(output_path, "r", encoding="utf-8") as _tf:
            transcription_text = _tf.read()

        videos_collection.update_one(
            {"video_id": video_id},
            {"$set": {
                "dubbed_url": dubbed_url,
                "transcript_url": transcript_url,
                "transcription": transcription_text,
                "vocals_url": vocals_url_out,
                "no_vocals_url": no_vocals_url_out,
                "updated_at": datetime.now(),
            }},
        )

        _publish_progress(self.request.id, "video_dub", 100, "Done")
        logger.info(f"[dub:{job_id}] Done → {dubbed_url}")
        return {
            "status": "completed",
            "dubbed_url": dubbed_url,
            "transcript_url": transcript_url,
            "vocals_url": vocals_url_out,
            "no_vocals_url": no_vocals_url_out,
            "video_id": video_id,
        }

    except Exception as exc:
        logger.error(f"[dub:{job_id}] Failed: {exc}")
        release_tts()
        release_whisper()
        raise self.retry(exc=exc, countdown=15)
