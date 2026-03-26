import gc
import logging
from typing import Optional

import torch
from faster_whisper import WhisperModel

from app.config import settings
from app.models.segment import TranscriptSegment, WordTimestamp

logger = logging.getLogger(__name__)

_model = None
_loaded_model_name = None


def get_model(model_name: Optional[str] = None) -> WhisperModel:
    global _model, _loaded_model_name
    name = model_name or settings.WHISPER_MODEL
    if _model is not None and _loaded_model_name != name:
        logger.info(f"Switching Whisper model from {_loaded_model_name} to {name}")
        release_model()
    if _model is None:
        logger.info(f"Loading Whisper model '{name}' on {settings.WHISPER_DEVICE}...")
        _model = WhisperModel(
            name,
            device=settings.WHISPER_DEVICE,
            compute_type=settings.WHISPER_COMPUTE_TYPE,
        )
        _loaded_model_name = name
        logger.info("Whisper model ready")
    return _model


def release_model() -> None:
    global _model, _loaded_model_name
    if _model is not None:
        logger.info("Releasing Whisper model from VRAM")
        del _model
        _model = None
        _loaded_model_name = None
        gc.collect()
        torch.cuda.empty_cache()


def transcribe_audio(
    audio_path: str,
    translate: bool = True,
    model_name: Optional[str] = None,
    language: Optional[str] = None,
) -> tuple[list[TranscriptSegment], str, float]:
    """
    Returns (segments, detected_language, duration_seconds).
    """
    logger.info(f"Transcribing audio: {audio_path}")
    model = get_model(model_name)
    transcribe_kwargs = dict(
        task="translate" if translate else "transcribe",
        beam_size=settings.WHISPER_BEAM_SIZE,
        word_timestamps=True,
        suppress_tokens=[],
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": settings.WHISPER_VAD_MIN_SILENCE_MS},
    )
    if language:
        transcribe_kwargs["language"] = language

    segments_gen, info = model.transcribe(audio_path, **transcribe_kwargs)
    logger.info(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")

    results = []
    last_end = 0.0
    for segment in segments_gen:
        text = segment.text.strip()
        results.append(TranscriptSegment(
            start=segment.start,
            end=segment.end,
            text=text,
            words=[
                WordTimestamp(word=w.word, start=w.start, end=w.end)
                for w in (segment.words or [])
            ],
        ))
        last_end = max(last_end, segment.end)
        logger.info(f"{'Translated' if translate else 'Transcribed'} segment [{segment.start:.2f}s - {segment.end:.2f}s]: {text}")

    duration = info.duration if hasattr(info, 'duration') and info.duration else last_end
    return results, info.language, duration
