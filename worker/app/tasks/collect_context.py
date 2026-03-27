import logging

from app.celery_app import celery
from app.config import settings
from app.services.llm_translator import collect_context as _collect_context

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.collect_context.collect_transcription_context")
def collect_transcription_context(
    segments: list[dict],
    model: str = None,
    custom_system_prompt: str = None,
) -> dict:
    if model is None:
        model = settings.OLLAMA_DEFAULT_MODEL
    logger.info(f"[collect_context] Collecting context for {len(segments)} segments using model={model}")
    context = _collect_context(segments, model=model, custom_system_prompt=custom_system_prompt)
    logger.info("[collect_context] Done")
    return {"context": context, "model": model}
