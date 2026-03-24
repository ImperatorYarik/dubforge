import ffmpeg
import os
import logging
import subprocess
import sys

from app.models.audio import SeparationResult

logger = logging.getLogger(__name__)


def _extract_audio(video_path: str, output_path: str) -> str:
    try:
        logger.info(f"Extracting audio from '{video_path}' to '{output_path}'")
        ffmpeg.input(video_path).output(output_path, acodec='pcm_s16le', ac=1, ar='16k').overwrite_output().run(quiet=True)
        logger.info(f"Audio extraction complete: {output_path}")
        return output_path
    except ffmpeg.Error as e:
        logger.error(f"Error extracting audio: {e}")
        return ""


def separate_sources(audio_path: str, output_dir: str) -> SeparationResult:
    logger.info(f"Separating sources from '{audio_path}' into '{output_dir}'")
    os.makedirs(output_dir, exist_ok=True)
    _extract_audio(audio_path, os.path.join(output_dir, "audio.wav"))
    try:
        subprocess.run([
            sys.executable, "-m", "demucs",
            "--two-stems", "vocals",
            "--out", output_dir,
            audio_path
        ], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Demucs source separation failed: {e}") from e

    name = os.path.splitext(os.path.basename(audio_path))[0]
    logger.info(f"Source separation complete. Outputs in: {output_dir}")
    return SeparationResult(
        vocals_path=f"{output_dir}/htdemucs/{name}/vocals.wav",
        no_vocals_path=f"{output_dir}/htdemucs/{name}/no_vocals.wav",
    )
