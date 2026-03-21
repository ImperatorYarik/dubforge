import gc
import logging
import torch
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

_model = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        logger.info("Loading Whisper model on CUDA...")
        _model = WhisperModel("large-v3", device="cuda", compute_type="int8")
        logger.info("Whisper model ready")
    return _model


def release_model() -> None:
    """Free Whisper VRAM so TTS can load without OOM."""
    global _model
    if _model is not None:
        logger.info("Releasing Whisper model from VRAM")
        del _model
        _model = None
        gc.collect()
        torch.cuda.empty_cache()


def transcribe_audio(audio_path: str, output_path: str | None, translate: bool = True) -> list:
    logger.info(f"Transcribing audio: {audio_path}")
    model = get_model()
    segments_gen, info = model.transcribe(
        audio_path,
        task="translate" if translate else "transcribe",
        beam_size=2,
        word_timestamps=True,
        suppress_tokens=[],
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300}
    )
    logger.info(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")
    results = []

    for segment in segments_gen:
        text = segment.text.strip()
        results.append({
            "start": segment.start,
            "end": segment.end,
            "text": text,
            "words": [
                {"word": w.word, "start": w.start, "end": w.end}
                for w in (segment.words or [])
            ],
        })
        logger.info(f"{'Translated' if translate else 'Transcribed'} segment [{segment.start:.2f}s - {segment.end:.2f}s]: {text}")
    return results