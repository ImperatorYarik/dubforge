import logging

from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT_SYSTEM = (
    "You are an expert content analyst. Given a transcript, produce a 2-4 sentence summary "
    "describing the topic, domain, speaker style, and any important domain-specific terminology. "
    "Return only the summary, no preamble or explanation."
)

_TRANSLATION_SYSTEM_TEMPLATE = (
    "You are a professional translator. Translate the following text into natural English. "
    "Use the context below to ensure accurate terminology and appropriate tone. "
    "Return only the translated text with no explanations and no additional output except for translated text.\n\nContext:\n{context}"
)


def collect_context(
    segments: list[dict],
    model: str,
    custom_system_prompt: str = None,
) -> str:
    client = OllamaClient()
    passage = " ".join(s.get("text", "") for s in segments)
    if len(passage) > 2000:
        passage = passage[:2000]
    system = custom_system_prompt if custom_system_prompt is not None else DEFAULT_CONTEXT_SYSTEM
    return client.generate(model=model, prompt=passage, system=system)


def translate_segment(
    text: str,
    context: str,
    model: str,
    source_language: str = None,
) -> str:
    client = OllamaClient()
    system = _TRANSLATION_SYSTEM_TEMPLATE.format(context=context)
    try:
        return client.generate(model=model, prompt=text, system=system)
    except Exception as e:
        logger.warning(f"LLM translation failed, using original text: {e}")
        return text
