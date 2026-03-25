import uuid
import logging

import redis as sync_redis

from app.config import settings
from app.celery_app import celery
from app.models.job import JobContext, SeparateJobResult
from app.pipelines.base import BasePipeline
from app.services.audio_repository import audio_repository
from app.services.progress_publisher import ProgressPublisher
from app.tasks.download import download_file_to_disk
from app.tasks.extract_audio import separate_sources

logger = logging.getLogger(__name__)

_redis = sync_redis.from_url(settings.REDIS_URL)


class DemucsPipeline(BasePipeline):
    abstract = True

    def execute(
        self,
        ctx: JobContext,
        progress: ProgressPublisher,
    ) -> SeparateJobResult:
        # Check for cached separation first — no need to re-download files
        video_doc = audio_repository._get_video_doc(ctx.video_id)
        if video_doc and video_doc.get("vocals_url"):
            progress.update("separate", 50, "Using cached audio separation")
            return SeparateJobResult(
                status="completed",
                video_id=ctx.video_id,
                vocals_url=video_doc["vocals_url"],
                no_vocals_url=video_doc.get("no_vocals_url", ""),
            )

        ext = ctx.input_url.split(".")[-1]
        src_path = f"{ctx.tmp_dir}/source.{ext}"

        progress.update("separate", 0, "Downloading video")
        if not download_file_to_disk(ctx.input_url, src_path):
            raise RuntimeError("Download failed")

        progress.update("separate", 20, "Separating audio sources with Demucs")
        result = separate_sources(src_path, ctx.tmp_dir)

        progress.update("separate", 80, "Uploading separated tracks")
        vocals_url, no_vocals_url = audio_repository.save_separation(
            ctx.video_id, ctx.project_id, ctx.job_id, result
        )

        return SeparateJobResult(
            status="completed",
            video_id=ctx.video_id,
            vocals_url=vocals_url,
            no_vocals_url=no_vocals_url,
        )


@celery.task(
    bind=True,
    max_retries=2,
    base=DemucsPipeline,
    name="app.pipelines.demucs_pipeline.separate_audio",
)
def separate_audio(self, project_id: str, video_id: str, input_url: str):
    job_id = str(uuid.uuid4())
    tmp_dir = self._make_tmp(job_id)
    ctx = JobContext(
        project_id=project_id,
        video_id=video_id,
        input_url=input_url,
        job_id=job_id,
        tmp_dir=tmp_dir,
    )
    logger.info(f"[separate:{job_id}] Starting. src={input_url}")
    progress = ProgressPublisher(_redis, self.request.id, settings.PROGRESS_TTL_SECONDS)
    try:
        result = self.execute(ctx, progress)
        self._cleanup_tmp(job_id)
        progress.update("separate", 100, "Done")
        logger.info(
            f"[separate:{job_id}] Done → vocals={result.vocals_url} no_vocals={result.no_vocals_url}"
        )
        return result.model_dump()
    except Exception as exc:
        logger.error(f"[separate:{job_id}] Failed: {exc}")
        raise self.retry(exc=exc, countdown=15)
