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
        _model = WhisperModel("large-v3", device="cuda", compute_type="int8_float16")
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


def translate_audio(audio_path: str, output_path: str) -> list:
    logger.info(f"Translating audio: {audio_path}")
    model = get_model()
    segments_gen, info = model.transcribe(
        audio_path,
        task="translate",
        beam_size=5,
    )
    logger.info(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")
    results = []

    for segment in segments_gen:
        text = segment.text.strip()
        results.append({
            "start": segment.start,
            "end": segment.end,
            "text": text,
        })
        logger.info(f"Translated segment [{segment.start:.2f}s - {segment.end:.2f}s]: {text}")

    logger.info(f"Writing transcription to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        for result in results:
            f.write(f"[{result['start']:.2f}s - {result['end']:.2f}s] {result['text']}\n")

    return results