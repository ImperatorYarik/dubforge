import os
import logging
import torch

# PyTorch 2.6+ defaults weights_only=True which breaks Coqui XTTS v2 checkpoint
# loading (it contains trusted custom classes). Patch before importing TTS.
_orig_torch_load = torch.load
def _torch_load_compat(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_torch_load(*args, **kwargs)
torch.load = _torch_load_compat

from TTS.api import TTS

logger = logging.getLogger(__name__)

MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
_tts = None

DEFAULT_SPEAKER = "Claribel Dervla"


def get_tts() -> TTS:
    global _tts
    if _tts is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading TTS model on {device}...")
        _tts = TTS(MODEL_NAME, progress_bar=False).to(device)
        logger.info("TTS model ready")
    return _tts


def synthesize(text: str, output_path: str, speaker: str = DEFAULT_SPEAKER) -> bool:
    """
    Synthesize text to WAV at output_path.

    speaker — either a built-in speaker name (e.g. "Claribel Dervla")
              or a path to a reference WAV file for voice cloning.
    """
    logger.info(f"Synthesizing: '{text[:50]}...' speaker={speaker}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        # If speaker is a file path, use voice-cloning mode (speaker_wav).
        # Otherwise treat it as a built-in speaker name.
        if os.path.isfile(speaker):
            get_tts().tts_to_file(
                text=text,
                file_path=output_path,
                speaker_wav=speaker,
                language="en",
            )
        else:
            get_tts().tts_to_file(
                text=text,
                file_path=output_path,
                speaker=speaker,
                language="en",
            )
        logger.info(f"Saved TTS to {output_path}")
        return True
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return False