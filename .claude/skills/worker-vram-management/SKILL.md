---
name: worker-vram-management
description: This skill should be used when loading or releasing AI models in the worker, designing VRAM lifecycle for new models, adding model loading sequences, or debugging OOM errors in the dubbing pipeline.
version: 1.0.0
---

# Worker VRAM Management

## The Problem

A single consumer GPU cannot hold Whisper large-v3 and XTTS v2 simultaneously — doing so causes OOM. The worker uses a strict sequential load/release pattern.

## Startup: Pre-load Whisper

Whisper is loaded once at worker startup via the `worker_process_init` signal in `celery_app.py`:
```python
from celery.signals import worker_process_init

@worker_process_init.connect
def preload_whisper(**kwargs):
    from app.services.model_manager import load_whisper
    load_whisper()
```

Whisper stays resident throughout the worker's lifetime, ready for transcription tasks.

## `release_model()` — Must Call Before Loading XTTS

Before loading XTTS v2 (TTS synthesis phase), Whisper MUST be released:
```python
def release_model(model) -> None:
    """Fully release a model from GPU memory."""
    del model
    import gc; gc.collect()
    import torch; torch.cuda.empty_cache()
```

This function lives in `services/model_manager.py`. Always import and call it — never inline the three steps.

## Pipeline Sequencing (Dubbing)

```
STARTUP:    [Whisper loaded] ─────────────────────────────────────────
TASK START: receive kwargs (video_url, vocals_url, segments, ...)
STEP 1:     download video from MinIO
STEP 2:     Demucs vocal separation (CPU/GPU, no Whisper/XTTS needed)
STEP 3:     Whisper transcription ← uses pre-loaded Whisper
STEP 4:     release_model(whisper) ← MANDATORY before XTTS
STEP 5:     load XTTS v2
STEP 6:     TTS synthesis for each segment
STEP 7:     release_model(xtts) ← always release in finally block
STEP 8:     ffmpeg audio mixing + video mux
STEP 9:     upload outputs to MinIO
```

## Safety Pattern: try/finally

Always wrap model loading in try/finally to guarantee release on error:
```python
xtts_model = None
try:
    xtts_model = load_xtts()
    # ... synthesis ...
finally:
    if xtts_model is not None:
        release_model(xtts_model)
```

## Adding a New Model

When introducing a third large model:
1. Identify its VRAM footprint.
2. Determine where in the pipeline it runs.
3. Ensure the model before it is released first.
4. Pre-load it at startup only if it's used in every job (otherwise load-on-demand).
5. Always wrap loading in try/finally.
6. Update `services/model_manager.py` with load/release functions for the new model.

## Common OOM Causes

| Cause | Fix |
|---|---|
| Forgot `release_model()` before XTTS | Call it after transcription, before TTS load |
| Exception bypasses release | Add try/finally around model load block |
| Two jobs running concurrently | Worker must use `solo` pool — check `celery_app.py` |
| Demucs + Whisper loaded simultaneously | Demucs releases GPU memory before Whisper phase |
