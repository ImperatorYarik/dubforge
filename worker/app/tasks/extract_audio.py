import ffmpeg
import os
import logging

logger = logging.getLogger(__name__)


def extract_audio(video_path: str, output_path: str) -> bool:
    try:
        logger.info(f"Extracting audio from '{video_path}' to '{output_path}'")
        ffmpeg.input(video_path).output(output_path, acodec='pcm_s16le', ac=1, ar='16k').overwrite_output().run(quiet=True)
        logger.info(f"Audio extraction complete: {output_path}")
        return True
    except ffmpeg.Error as e:
        logger.error(f"Error extracting audio: {e}")
        return False