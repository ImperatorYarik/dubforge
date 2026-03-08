import os
import subprocess
import logging
import json

logger = logging.getLogger(__name__)


def get_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", path],
        capture_output=True, text=True, check=True
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def build_atempo_filter(ratio: float) -> str:
    """Build chained atempo filter string for any ratio."""
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
    """Time-stretch input_wav to exactly target_duration seconds."""
    src_dur = get_duration(input_wav)
    ratio = src_dur / target_duration
    ratio = max(0.4, min(ratio, 2.5))

    atempo = build_atempo_filter(ratio)
    logger.info(f"Stretching {src_dur:.2f}s → {target_duration:.2f}s (ratio={ratio:.3f}, filter={atempo})")

    cmd = [
        "ffmpeg", "-y", "-i", input_wav,
        "-filter:a", atempo,
        output_wav
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        logger.error(f"stretch failed: {result.stderr.decode()}")
        return False
    return True


def build_dubbed_audio(
    original_audio: str,
    segments: list[dict],
    output_wav: str,
    duck_volume: float = 0.1,
) -> bool:
    """
    Mix original audio (ducked during speech) with TTS clips.
    
    segments: each dict must have: start, end, tts_wav (path to stretched TTS clip)
    duck_volume: 0.0 = silence original during speech, 1.0 = no ducking
    """
    total_dur = get_duration(original_audio)

    inputs = ["-i", original_audio]
    filter_parts = []
    labels = []

    if duck_volume == 0.0:
        # Completely mute the original — don't include it in the mix at all
        pass
    else:
        # Build volume envelope: 1.0 normally, duck_volume during speech segments
        if segments:
            duck_parts = "+".join([
                f"between(t,{s['start']},{s['end']})*{duck_volume - 1}"
                for s in segments
            ])
            duck_expr = f"1+{duck_parts}"
        else:
            duck_expr = "1"
        filter_parts.append(f"[0:a]volume='{duck_expr}'[orig]")
        labels.append("[orig]")

    for i, seg in enumerate(segments, start=1):
        inputs += ["-i", seg["tts_wav"]]
        delay_ms = int(seg["start"] * 1000)
        filter_parts.append(
            f"[{i}:a]adelay={delay_ms}|{delay_ms}[tts{i}]"
        )
        labels.append(f"[tts{i}]")

    n = len(labels)
    all_inputs = "".join(labels)
    filter_parts.append(
        f"{all_inputs}amix=inputs={n}:duration=longest:normalize=0[out]"
    )

    filter_complex = "; ".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-t", str(total_dur),
        output_wav,
    ]

    logger.info(f"Building dubbed audio: {n} TTS clips + ducked original")
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        logger.error(f"mix failed: {result.stderr.decode()}")
        return False

    logger.info(f"Dubbed audio ready: {output_wav}")
    return True


def mux_audio_into_video(video_path: str, audio_path: str, output_path: str) -> bool:
    """Replace video audio track. Stream-copies video — no re-encode."""
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
        logger.error(f"mux failed: {result.stderr.decode()}")
        return False
    logger.info(f"Mux complete: {output_path}")
    return True