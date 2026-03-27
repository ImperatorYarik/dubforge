import uuid
import logging
from typing import Optional

import redis as sync_redis

from app.config import settings
from app.celery_app import celery
from app.models.job import JobContext, TranscribeJobResult
from app.models.audio import SeparationResult
from app.models.segment import TranscriptSegment
from app.pipelines.base import BasePipeline
from app.services.audio_repository import audio_repository
from app.services.model_manager import model_manager
from app.services.progress_publisher import ProgressPublisher
from app.services.transcript_repository import transcript_repository
from app.tasks.download import download_file_to_disk
from app.tasks.extract_audio import separate_sources, _extract_audio
from app.tasks.transcribe import transcribe_audio

logger = logging.getLogger(__name__)

_redis = sync_redis.from_url(settings.REDIS_URL)


class TranscribePipeline(BasePipeline):
    abstract = True

    def execute(
        self,
        ctx: JobContext,
        translate: bool,
        progress: ProgressPublisher,
        model: str = "large-v3",
        skip_demucs: bool = False,
        language: Optional[str] = None,
        vocals_url: Optional[str] = None,
        no_vocals_url: Optional[str] = None,
    ) -> TranscribeJobResult:
        separation = self._ensure_vocals(ctx, progress, skip_demucs, vocals_url, no_vocals_url)
        segments, detected_language, duration_seconds = self._transcribe(
            ctx, separation, translate, progress, model, language
        )
        transcript_url = transcript_repository.save_transcription(
            ctx.project_id,
            ctx.job_id,
            segments,
            ctx.tmp_dir,
            detected_language=detected_language,
            duration_seconds=duration_seconds,
        )
        transcription_text = "".join(
            f"[{s.start:.2f}s - {s.end:.2f}s] {s.text}\n" for s in segments
        )
        return TranscribeJobResult(
            status="completed",
            video_id=ctx.video_id,
            transcript_url=transcript_url,
            transcription=transcription_text,
            transcript_segments=[
                {"start": s.start, "end": s.end, "text": s.text} for s in segments
            ],
            detected_language=detected_language,
            duration_seconds=duration_seconds,
        )

    def _ensure_vocals(
        self,
        ctx: JobContext,
        progress: ProgressPublisher,
        skip_demucs: bool,
        vocals_url: Optional[str],
        no_vocals_url: Optional[str],
    ) -> SeparationResult:
        cached = audio_repository.download_cached_separation(vocals_url, no_vocals_url, ctx.tmp_dir)
        if cached:
            progress.update("transcribe", 5, "Downloading extracted audio")
            progress.update("transcribe", 20, "Audio ready")
            return cached

        ext = ctx.input_url.split(".")[-1]
        src_path = f"{ctx.tmp_dir}/source.{ext}"
        progress.update("transcribe", 0, "Downloading video")
        if not download_file_to_disk(ctx.input_url, src_path):
            raise RuntimeError("Download failed")

        if skip_demucs:
            progress.update("transcribe", 10, "Extracting audio (Demucs skipped)")
            audio_path = f"{ctx.tmp_dir}/audio.wav"
            _extract_audio(src_path, audio_path)
            result = SeparationResult(vocals_path=audio_path, no_vocals_path=audio_path)
            progress.update("transcribe", 20, "Audio extraction complete")
            return result

        progress.update("transcribe", 10, "Separating audio sources")
        result = separate_sources(src_path, ctx.tmp_dir)

        progress.update("transcribe", 18, "Uploading extracted audio")
        audio_repository.save_separation(ctx.project_id, ctx.job_id, result)
        progress.update("transcribe", 20, "Audio extraction complete")
        return result

    def _transcribe(
        self,
        ctx: JobContext,
        separation: SeparationResult,
        translate: bool,
        progress: ProgressPublisher,
        model: str = "large-v3",
        language: Optional[str] = None,
    ) -> tuple[list[TranscriptSegment], str, float]:
        progress.update("transcribe", 25, "Starting transcription")
        segments, detected_language, duration_seconds = transcribe_audio(
            separation.vocals_path,
            translate=translate,
            model_name=model,
            language=language,
        )
        progress.update("transcribe", 90, "Transcription complete")
        return segments, detected_language, duration_seconds


@celery.task(bind=True, max_retries=2, base=TranscribePipeline, name="app.pipelines.transcribe_pipeline.transcribe_video")
def transcribe_video(
    self,
    project_id: str,
    video_id: str,
    input_url: str,
    translate: bool = True,
    model: str = "large-v3",
    skip_demucs: bool = False,
    language: Optional[str] = None,
    vocals_url: Optional[str] = None,
    no_vocals_url: Optional[str] = None,
):
    job_id = str(uuid.uuid4())
    tmp_dir = self._make_tmp(job_id)
    ctx = JobContext(project_id=project_id, video_id=video_id, input_url=input_url, job_id=job_id, tmp_dir=tmp_dir)
    logger.info(f"[transcribe:{job_id}] Starting. src={input_url}")
    progress = ProgressPublisher(_redis, self.request.id, settings.PROGRESS_TTL_SECONDS)
    try:
        result = self.execute(
            ctx, translate, progress,
            model=model,
            skip_demucs=skip_demucs,
            language=language,
            vocals_url=vocals_url,
            no_vocals_url=no_vocals_url,
        )
        self._cleanup_tmp(job_id)
        progress.update("transcribe", 100, "Done")
        logger.info(f"[transcribe:{job_id}] Done → {result.transcript_url}")
        return result.model_dump()
    except Exception as exc:
        logger.error(f"[transcribe:{job_id}] Failed: {exc}")
        model_manager.release_all()
        raise self.retry(exc=exc, countdown=15)
