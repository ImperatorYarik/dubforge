import uuid
import logging
import subprocess
from datetime import datetime
from typing import Optional

import redis as sync_redis

from app.config import settings
from app.celery_app import celery
from app.database import videos_collection
from app.models.audio import SeparationResult, VoiceReferenceResult
from app.models.job import JobContext, DubJobResult
from app.models.segment import TranscriptSegment
from app.pipelines.base import BasePipeline
from app.services.audio_repository import audio_repository
from app.services.model_manager import model_manager
from app.services.progress_publisher import ProgressPublisher
from app.services.transcript_repository import transcript_repository
from app.tasks.audio_mix import stretch_clip, build_dubbed_audio, mux_audio_into_video
from app.tasks.download import download_file_to_disk
from app.tasks.extract_audio import separate_sources
from app.tasks.reference_audio import extract_reference_wav
from app.tasks.transcribe import transcribe_audio
from app.tasks.tts import synthesize
from app.tasks.phrase_split import split_into_phrases
from app.tasks.upload import upload_to_s3

logger = logging.getLogger(__name__)

_redis = sync_redis.from_url(settings.REDIS_URL)


class DubbingPipeline(BasePipeline):
    abstract = True

    def execute(
        self,
        ctx: JobContext,
        progress: ProgressPublisher,
        skip_transcription: bool,
        ducking_enabled: bool = True,
        ducking_level: float = 0.3,
        atempo_min: float = None,
        atempo_max: float = None,
    ) -> DubJobResult:
        if atempo_min is None:
            atempo_min = settings.ATEMPO_MIN
        if atempo_max is None:
            atempo_max = settings.ATEMPO_MAX

        ext = ctx.input_url.split(".")[-1]

        progress.update("video_dub", 0, "Downloading source video…")
        src_path = self._download_source(ctx, ext)
        progress.update("video_dub", 5, "Download complete")

        progress.update("video_dub", 10, "Separating vocals from background (Demucs)…")
        separation = self._ensure_vocals(ctx, src_path, progress)

        segments, detected_language, duration_seconds, transcript_path = self._ensure_transcription(
            ctx, separation, skip_transcription, progress
        )

        ref = extract_reference_wav(
            separation.vocals_path, segments, f"{ctx.tmp_dir}/speaker_ref.wav"
        )
        model_manager.release_whisper()
        progress.update("video_dub", 53, "Synthesizing dubbed audio…")

        segments = self._synthesize_segments(ctx, segments, ref, progress, atempo_min, atempo_max)
        model_manager.release_tts()

        progress.update("video_dub", 80, "Mixing dubbed audio with background…")
        dubbed_audio = self._mix_audio(ctx, separation, segments, ducking_enabled, ducking_level)

        progress.update("video_dub", 90, "Muxing audio into video…")
        dubbed_video = self._mux_video(ctx, src_path, dubbed_audio, ext)

        progress.update("video_dub", 95, "Uploading results…")
        return self._upload_and_persist(
            ctx, dubbed_video, transcript_path, separation, ext,
            detected_language, duration_seconds, segments
        )

    def _download_source(self, ctx: JobContext, ext: str) -> str:
        src_path = f"{ctx.tmp_dir}/source.{ext}"
        if not download_file_to_disk(ctx.input_url, src_path):
            raise RuntimeError("Download failed")
        return src_path

    def _ensure_vocals(
        self, ctx: JobContext, src_path: str, progress: ProgressPublisher
    ) -> SeparationResult:
        cached = audio_repository.download_cached_separation(ctx.video_id, ctx.tmp_dir)
        if cached:
            progress.update("video_dub", 8, "Downloading previously extracted audio…")
            progress.update("video_dub", 15, "Audio ready")
            return cached

        result = separate_sources(src_path, ctx.tmp_dir)
        progress.update("video_dub", 18, "Uploading extracted audio…")
        audio_repository.save_separation(ctx.video_id, ctx.project_id, ctx.job_id, result)
        progress.update("video_dub", 20, "Audio extraction complete")
        return result

    def _ensure_transcription(
        self,
        ctx: JobContext,
        separation: SeparationResult,
        skip_transcription: bool,
        progress: ProgressPublisher,
    ) -> tuple[list[TranscriptSegment], Optional[str], Optional[float], str]:
        transcript_path = f"{ctx.tmp_dir}/transcription.txt"
        detected_language = None
        duration_seconds = None

        if skip_transcription:
            existing = transcript_repository.get_existing(ctx.video_id)
            if existing is None:
                raise RuntimeError("No parseable segments in existing transcription")
            segments, transcription_text = existing
            # Try to recover stored language/duration from MongoDB
            from app.database import videos_collection as vc
            video_doc = vc.find_one({"video_id": ctx.video_id})
            if video_doc:
                detected_language = video_doc.get("detected_language")
                duration_seconds = video_doc.get("duration_seconds")
            progress.update("video_dub", 22, "Loading existing transcription…")
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcription_text)
            progress.update("video_dub", 50, "Transcription ready — loading TTS model…")
            return segments, detected_language, duration_seconds, transcript_path

        progress.update("video_dub", 25, "Transcribing audio (Whisper)…")
        segments, detected_language, duration_seconds = transcribe_audio(
            separation.vocals_path, translate=True
        )
        with open(transcript_path, "w", encoding="utf-8") as f:
            for seg in segments:
                f.write(f"[{seg.start:.2f}s - {seg.end:.2f}s] {seg.text}\n")
        progress.update("video_dub", 50, "Transcription complete — loading TTS model…")
        return segments, detected_language, duration_seconds, transcript_path

    def _synthesize_segments(
        self,
        ctx: JobContext,
        segments: list[TranscriptSegment],
        ref: VoiceReferenceResult,
        progress: ProgressPublisher,
        atempo_min: float,
        atempo_max: float,
    ) -> list[TranscriptSegment]:
        all_phrases: list[TranscriptSegment] = []

        for i, seg in enumerate(segments):
            pct = 55 + int((i / len(segments)) * 23)
            progress.update("video_dub", pct, f"Synthesizing segment {i + 1}/{len(segments)}…")

            phrases = split_into_phrases(seg, gap_ms=settings.PHRASE_GAP_THRESHOLD_MS)

            for j, phrase in enumerate(phrases):
                window = phrase.end - phrase.start
                raw_tts = f"{ctx.tmp_dir}/tts_raw_{i}_{j}.wav"
                stretched_tts = f"{ctx.tmp_dir}/tts_{i}_{j}.wav"

                if not synthesize(phrase.text, raw_tts, speaker=ref.wav_path, ref_text=ref.reference_text):
                    logger.warning(f"[dub:{ctx.job_id}] TTS failed for segment {i} phrase {j}, using silence")
                    subprocess.run([
                        "ffmpeg", "-y", "-f", "lavfi",
                        "-i", f"anullsrc=r=22050:cl=mono:d={window}",
                        stretched_tts,
                    ], check=True, capture_output=True)
                else:
                    if not stretch_clip(raw_tts, stretched_tts, window, atempo_min, atempo_max):
                        raise RuntimeError(f"Stretch failed for segment {i} phrase {j}")

                phrase.tts_wav = stretched_tts
                all_phrases.append(phrase)

        return all_phrases

    def _mix_audio(
        self,
        ctx: JobContext,
        separation: SeparationResult,
        segments: list[TranscriptSegment],
        ducking_enabled: bool,
        ducking_level: float,
    ) -> str:
        dubbed_audio = f"{ctx.tmp_dir}/dubbed_audio.wav"
        duck_vol = ducking_level if ducking_enabled else 1.0
        if not build_dubbed_audio(
            separation.no_vocals_path,
            segments,
            dubbed_audio,
            duck_volume=duck_vol,
            ducking_enabled=ducking_enabled,
        ):
            raise RuntimeError("Audio mix failed")
        return dubbed_audio

    def _mux_video(
        self, ctx: JobContext, src_path: str, dubbed_audio: str, ext: str
    ) -> str:
        dubbed_video = f"{ctx.tmp_dir}/dubbed.{ext}"
        if not mux_audio_into_video(src_path, dubbed_audio, dubbed_video):
            raise RuntimeError("Mux failed")
        return dubbed_video

    def _upload_and_persist(
        self,
        ctx: JobContext,
        dubbed_video: str,
        transcript_path: str,
        separation: SeparationResult,
        ext: str,
        detected_language: Optional[str],
        duration_seconds: Optional[float],
        segments: list[TranscriptSegment],
    ) -> DubJobResult:
        dubbed_url = upload_to_s3(dubbed_video, f"{ctx.project_id}/dubbed_{ctx.job_id}.{ext}")
        transcript_url = upload_to_s3(transcript_path, f"{ctx.project_id}/transcription_{ctx.job_id}.txt")
        vocals_url = upload_to_s3(separation.vocals_path, f"{ctx.project_id}/vocals_{ctx.job_id}.wav")
        no_vocals_url = upload_to_s3(separation.no_vocals_path, f"{ctx.project_id}/no_vocals_{ctx.job_id}.wav")

        with open(transcript_path, "r", encoding="utf-8") as f:
            transcription_text = f.read()

        update_fields = {
            "dubbed_url": dubbed_url,
            "transcript_url": transcript_url,
            "transcription": transcription_text,
            "transcript_segments": [
                {"start": s.start, "end": s.end, "text": s.text}
                for s in segments
            ],
            "vocals_url": vocals_url,
            "no_vocals_url": no_vocals_url,
            "updated_at": datetime.now(),
        }
        if detected_language:
            update_fields["detected_language"] = detected_language
        if duration_seconds is not None:
            update_fields["duration_seconds"] = duration_seconds

        videos_collection.update_one(
            {"video_id": ctx.video_id},
            {"$set": update_fields},
        )

        return DubJobResult(
            status="completed",
            dubbed_url=dubbed_url,
            transcript_url=transcript_url,
            vocals_url=vocals_url,
            no_vocals_url=no_vocals_url,
            video_id=ctx.video_id,
        )


@celery.task(bind=True, max_retries=2, base=DubbingPipeline, name="app.pipelines.dubbing_pipeline.dub_video")
def dub_video(
    self,
    project_id: str,
    video_id: str,
    input_url: str,
    remove_original_audio: bool = True,
    skip_transcription: bool = False,
    ducking_enabled: bool = True,
    ducking_level: float = 0.3,
    atempo_min: float = None,
    atempo_max: float = None,
):
    job_id = str(uuid.uuid4())
    tmp_dir = self._make_tmp(job_id)
    ctx = JobContext(project_id=project_id, video_id=video_id, input_url=input_url, job_id=job_id, tmp_dir=tmp_dir)
    logger.info(f"[dub:{job_id}] Starting. src={input_url} skip_transcription={skip_transcription}")
    progress = ProgressPublisher(_redis, self.request.id, settings.PROGRESS_TTL_SECONDS)
    try:
        result = self.execute(
            ctx, progress, skip_transcription,
            ducking_enabled=ducking_enabled,
            ducking_level=ducking_level,
            atempo_min=atempo_min,
            atempo_max=atempo_max,
        )
        self._cleanup_tmp(job_id)
        progress.update("video_dub", 100, "Done")
        logger.info(f"[dub:{job_id}] Done → {result.dubbed_url}")
        return result.model_dump()
    except Exception as exc:
        logger.error(f"[dub:{job_id}] Failed: {exc}")
        model_manager.release_all()
        raise self.retry(exc=exc, countdown=15)
