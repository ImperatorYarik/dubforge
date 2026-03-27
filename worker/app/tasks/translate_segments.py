import logging

from app.celery_app import celery
from app.config import settings
from app.services.llm_translator import translate_segment

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.translate_segments.translate_segments_batch")
def translate_segments_batch(
    segments: list[dict],
    context: str,
    model: str = None,
) -> dict:
    if model is None:
        model = settings.OLLAMA_DEFAULT_MODEL
    total = len(segments)
    logger.info(f"[translate_segments] Translating {total} segments using model={model}")

    translated = []
    for i, seg in enumerate(segments):
        translated_text = translate_segment(
            text=seg["text"],
            context=context,
            model=model,
        )
        translated.append({**seg, "text": translated_text})
        logger.debug(f"[translate_segments] {i + 1}/{total} done")

    logger.info("[translate_segments] Done")
    return {"segments": translated}
