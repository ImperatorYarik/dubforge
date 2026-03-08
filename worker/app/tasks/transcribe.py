import logging
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

_model = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        logger.info("Loading Whisper model on CUDA...")
        _model = WhisperModel("turbo", device="cuda", compute_type="float16")
        logger.info("Whisper model ready")
    return _model


def transcribe_audio(audio_path: str, output_path: str) -> str:
    logger.info(f"Transcribing audio: {audio_path}")
    model = get_model()
    segments, info = model.transcribe(
        audio_path,
        log_progress=True,
        beam_size=5
    )

    logger.info(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")

    total_duration = info.duration
    last_logged_pct = -1

    with open(output_path, "w", encoding="utf-8") as f:
        for segment in segments:
            f.write(segment.text.strip() + "\n")

            if total_duration:
                pct = int((segment.end / total_duration) * 100)
                # log every 10%
                if pct // 10 > last_logged_pct // 10:
                    logger.info(f"Transcription progress: {pct}% ({segment.end:.1f}s / {total_duration:.1f}s)")
                    last_logged_pct = pct

    logger.info(f"Transcription complete (100%): {output_path}")
    return output_path