import os
import subprocess
import logging
import json

from app.config import settings
from app.models.segment import TranscriptSegment

logger = logging.getLogger(__name__)


def get_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", path],
        capture_output=True, text=True, check=True
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def build_atempo_filter(ratio: float) -> str:
    """Build chained atempo filter string for ratios outside the [0.5, 2.0] single-filter range."""
    filters = []
    r = ratio
    while r > 2.0:
        filters.append("atempo=2.0")
        r /= 2.0
    while r < 0.5:
        filters.append("atempo=0.5")
        r /= 0.5
    filters.append(f"atempo={r:.6f}")
    return ",".join(filters)


def stretch_clip(input_wav: str, output_wav: str, target_duration: float) -> bool:
    src_dur = get_duration(input_wav)
    ratio = src_dur / target_duration
    clamped = max(settings.ATEMPO_MIN, min(ratio, settings.ATEMPO_MAX))

    atempo = build_atempo_filter(clamped)
    fade_start = max(0.0, target_duration - 0.05)
    logger.info(
        f"Stretching {src_dur:.2f}s → {target_duration:.2f}s "
        f"(ratio={clamped:.3f}{' clamped' if clamped != ratio else ''})"
    )

    cmd = [
        "ffmpeg", "-y", "-i", input_wav,
        "-filter:a", f"{atempo},afade=t=out:st={fade_start:.3f}:d=0.05",
        "-t", str(target_duration),
        output_wav,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        logger.error(f"stretch failed: {result.stderr.decode()}")
        return False
    return True


def build_dubbed_audio(
    original_audio: str,
    segments: list[TranscriptSegment],
    output_wav: str,
    duck_volume: float = settings.DUCK_VOLUME,
) -> bool:
    total_dur = get_duration(original_audio)

    inputs = ["-i", original_audio]
    filter_parts = []
    labels = []

    if duck_volume != 0.0:
        if segments:
            duck_parts = "+".join([
                f"between(t,{s.start},{s.end})*{duck_volume - 1}"
                for s in segments
            ])
            duck_expr = f"1+{duck_parts}"
        else:
            duck_expr = "1"
        filter_parts.append(f"[0:a]volume='{duck_expr}'[orig]")
        labels.append("[orig]")

    for i, seg in enumerate(segments, start=1):
        inputs += ["-i", seg.tts_wav]
        delay_ms = int(seg.start * 1000)
        filter_parts.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[tts{i}]")
        labels.append(f"[tts{i}]")

    n = len(labels)
    all_inputs = "".join(labels)
    filter_parts.append(f"{all_inputs}amix=inputs={n}:duration=longest:normalize=0[out]")

    filter_complex = "; ".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-t", str(total_dur),
        output_wav,
    ]

    logger.info(f"Building dubbed audio: {n} inputs (1 background + {n - 1} TTS clips) → '{output_wav}'")
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        logger.error(f"Mix failed (exit {result.returncode}): {result.stderr.decode()}")
        return False

    logger.info(f"Dubbed audio ready: {output_wav}")
    return True


def mux_audio_into_video(video_path: str, audio_path: str, output_path: str) -> bool:
    """Replace video audio track. Stream-copies video — no re-encode."""
    logger.info(f"Muxing video='{video_path}' + audio='{audio_path}' → '{output_path}'")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        logger.error(f"Mux failed (exit {result.returncode}): {result.stderr.decode()}")
        return False
    logger.info(f"Mux complete: {output_path}")
    return True
