import gc
import logging
import os
import warnings

import torch

logger = logging.getLogger(__name__)

logging.getLogger("TTS").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)

warnings.filterwarnings("ignore", category=FutureWarning, module=r"TTS\..*")
warnings.filterwarnings("ignore", category=FutureWarning, module=r"transformers\..*")
warnings.filterwarnings("ignore", message=".*attention mask.*", category=UserWarning)

_tts = None


def get_tts():
    global _tts
    if _tts is None:
        from TTS.api import TTS
        from app.config import settings
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading XTTS v2 on {device}...")
        _tts = TTS(settings.XTTS_MODEL).to(device)
        logger.info("XTTS v2 ready")
    return _tts


def release_model() -> None:
    global _tts
    if _tts is not None:
        logger.info("Releasing XTTS v2 from VRAM")
        del _tts
        _tts = None
        gc.collect()
        torch.cuda.empty_cache()


def synthesize_builtin(text: str, output_path: str, speaker_name: str) -> bool:
    logger.info(f"Synthesizing (builtin speaker={speaker_name}): '{text[:50]}'")
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        get_tts().tts_to_file(
            text=text,
            speaker=speaker_name,
            language="en",
            file_path=output_path,
        )
        logger.info(f"Saved TTS to {output_path}")
        return True
    except Exception as e:
        logger.error(f"XTTS synthesis failed: {e}")
        return False


def synthesize(text: str, output_path: str, speaker: str, ref_text: str = "") -> bool:
    """
    Synthesize text to WAV using XTTS v2 zero-shot voice cloning.

    speaker — path to a reference WAV (3–30s of clean speech).
    """
    logger.info(f"Synthesizing: '{text[:50]}...' speaker={speaker}")

    if not speaker or not os.path.isfile(speaker):
        logger.error("XTTS v2 requires a reference WAV path as speaker")
        return False

    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        get_tts().tts_to_file(
            text=text,
            speaker_wav=speaker,
            language="en",
            file_path=output_path,
        )
        logger.info(f"Saved TTS to {output_path}")
        return True
    except Exception as e:
        logger.error(f"XTTS synthesis failed: {e}")
        return False
