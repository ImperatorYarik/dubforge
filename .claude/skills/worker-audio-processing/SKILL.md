---
name: worker-audio-processing
description: This skill should be used when writing audio processing code in the worker — XTTS voice cloning constraints, atempo stretch clamping, reference audio preparation, Demucs vocal separation, audio ducking, or ffmpeg audio/video operations.
version: 1.0.0
---

# Worker Audio Processing

## XTTS v2 Constraints

### Mono input only
XTTS expects **mono** audio for the reference/speaker WAV. Always downmix stereo to mono before passing:
```python
import librosa
audio, sr = librosa.load(reference_path, sr=22050, mono=True)
```
Or with ffmpeg:
```bash
ffmpeg -i stereo.wav -ac 1 mono.wav
```

### Voice reference from longest segments
Build the reference WAV by concatenating the longest speech segments until total duration ≥ 8 seconds (`REFERENCE_AUDIO_MIN_SECONDS` from config). This gives XTTS enough voice sample to clone from:
```python
segments_sorted = sorted(segments, key=lambda s: s.end - s.start, reverse=True)
selected = []
total_duration = 0.0
for seg in segments_sorted:
    selected.append(seg)
    total_duration += seg.end - seg.start
    if total_duration >= settings.REFERENCE_AUDIO_MIN_SECONDS:
        break
```

## Atempo Time-Stretching

TTS clips must be stretched to match original segment duration. Clamp the ratio to prevent unintelligible audio:

```python
ATEMPO_MIN = 0.75  # from config
ATEMPO_MAX = 1.50

ratio = tts_duration / segment_duration
ratio = max(ATEMPO_MIN, min(ATEMPO_MAX, ratio))
```

ffmpeg atempo filter (values outside [0.5, 2.0] require chaining):
```python
# For ratios in [0.75, 1.5] a single atempo filter suffices:
ffmpeg_filter = f"atempo={ratio:.4f}"
```

After stretching, **hard-trim** the clip to the exact segment duration and apply a 50ms fade-out to prevent audio bleed into the next segment:
```python
# ffmpeg trim + afade
"-af", f"atempo={ratio:.4f},atrim=duration={segment_duration},afade=t=out:st={segment_duration - 0.05}:d=0.05"
```

## Audio Ducking

During dubbed speech segments, the background (no-vocals) track is ducked to a configurable level, then restored in silence:
- Use ffmpeg `volume` filter with per-segment timeline expressions, or `sidechaincompress`.
- Configurable duck level via `config.py` (e.g. `DUCK_LEVEL_DB = -12`).

## Demucs Vocal Separation

Uses `htdemucs` model with `--two-stems vocals`:
```bash
demucs --two-stems vocals --name htdemucs -o {output_dir} {input_file}
```
Produces:
- `vocals.wav` — isolated speech
- `no_vocals.wav` — background music/noise

Both are uploaded to MinIO after separation. URLs are cached in MongoDB by the API so subsequent re-dubs skip Demucs entirely.

## ffmpeg Operations Reference

**Extract audio from video:**
```bash
ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 44100 audio.wav
```

**Mux dubbed audio back into video:**
```bash
ffmpeg -i original_video.mp4 -i dubbed_audio.wav -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 output.mp4
```

**Convert to mono 22050 Hz (XTTS reference):**
```bash
ffmpeg -i input.wav -ac 1 -ar 22050 reference_mono.wav
```

## Audio Quality Rules

- Always use 16-bit PCM WAV for intermediate files (lossless, fast).
- XTTS output is WAV; convert to AAC only at final mux stage.
- Preserve original video codec (`-c:v copy`) — never re-encode video unnecessarily.
