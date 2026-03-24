import gc
import logging
import torch
from faster_whisper import WhisperModel

from app.config import settings
from app.models.segment import TranscriptSegment, WordTimestamp

logger = logging.getLogger(__name__)

_model = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        logger.info(f"Loading Whisper model on {settings.WHISPER_DEVICE}...")
        _model = WhisperModel(
            settings.WHISPER_MODEL,
            device=settings.WHISPER_DEVICE,
            compute_type=settings.WHISPER_COMPUTE_TYPE,
        )
        logger.info("Whisper model ready")
    return _model


def release_model() -> None:
    global _model
    if _model is not None:
        logger.info("Releasing Whisper model from VRAM")
        del _model
        _model = None
        gc.collect()
        torch.cuda.empty_cache()


def transcribe_audio(audio_path: str, translate: bool = True) -> list[TranscriptSegment]:
    logger.info(f"Transcribing audio: {audio_path}")
    model = get_model()
    segments_gen, info = model.transcribe(
        audio_path,
        task="translate" if translate else "transcribe",
        beam_size=settings.WHISPER_BEAM_SIZE,
        word_timestamps=True,
        suppress_tokens=[],
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": settings.WHISPER_VAD_MIN_SILENCE_MS},
    )
    logger.info(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")

    results = []
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
        logger.info(f"{'Translated' if translate else 'Transcribed'} segment [{segment.start:.2f}s - {segment.end:.2f}s]: {text}")
    return results
