import logging

import numpy as np
import soundfile as sf

from app.config import settings
from app.models.audio import VoiceReferenceResult
from app.models.segment import TranscriptSegment

logger = logging.getLogger(__name__)


def extract_reference_wav(
    vocals_path: str,
    segments: list[TranscriptSegment],
    output_path: str,
    target_dur: float = settings.VOICE_REF_TARGET_DURATION,
) -> VoiceReferenceResult:
    audio, sr = sf.read(vocals_path)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)

    min_chunk_samples = int(settings.VOICE_REF_MIN_CHUNK_DURATION * sr)
    sorted_segs = sorted(segments, key=lambda s: s.end - s.start, reverse=True)
    chunks = []
    total = 0.0

    for seg in sorted_segs:
        start = max(0, int(seg.start * sr))
        end = min(len(audio), int(seg.end * sr))
        chunk = audio[start:end]
        if len(chunk) > min_chunk_samples:
            chunks.append(chunk)
            total += len(chunk) / sr
        if total >= target_dur:
            break

    if not chunks:
        raise RuntimeError("No usable audio segments for voice reference")

    ref_audio = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]
    sf.write(output_path, ref_audio, sr)
    logger.info(f"Built {total:.1f}s voice reference from {len(chunks)} segment(s)")

    return VoiceReferenceResult(wav_path=output_path, reference_text=sorted_segs[0].text)
