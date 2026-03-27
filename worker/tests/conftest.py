"""
conftest.py — session-level stubs for GPU packages unavailable outside the
worker container (torch, faster-whisper).  These are inserted into sys.modules
before any app import so that top-level `import torch` / `from faster_whisper
import WhisperModel` statements in the task modules don't raise ModuleNotFoundError.
"""

import sys
import types
from unittest.mock import MagicMock
import pytest

from app.models.job import JobContext
from app.models.audio import SeparationResult, VoiceReferenceResult
from app.models.segment import TranscriptSegment, WordTimestamp


# ---------------------------------------------------------------------------
# GPU package stubs — inserted once at collection time
# ---------------------------------------------------------------------------

def _make_torch_stub() -> types.ModuleType:
    torch = types.ModuleType("torch")
    cuda = types.ModuleType("torch.cuda")
    cuda.empty_cache = MagicMock()
    cuda.is_available = MagicMock(return_value=False)
    torch.cuda = cuda
    return torch


def _make_faster_whisper_stub() -> types.ModuleType:
    fw = types.ModuleType("faster_whisper")
    fw.WhisperModel = MagicMock()
    return fw


for _name, _mod in [
    ("torch", _make_torch_stub()),
    ("torch.cuda", _make_torch_stub().cuda),
    ("faster_whisper", _make_faster_whisper_stub()),
]:
    sys.modules.setdefault(_name, _mod)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ctx(tmp_path):
    return JobContext(
        project_id="proj1",
        video_id="vid1",
        input_url="http://minio:9000/bucket/proj1/video.mp4",
        job_id="job1",
        tmp_dir=str(tmp_path),
    )


@pytest.fixture
def mock_progress():
    return MagicMock()


@pytest.fixture
def mock_separation():
    return SeparationResult(
        vocals_path="/tmp/test/vocals.wav",
        no_vocals_path="/tmp/test/no_vocals.wav",
    )


@pytest.fixture
def mock_segments():
    return [TranscriptSegment(start=0.0, end=5.0, text="Hello world")]


@pytest.fixture
def mock_ref():
    return VoiceReferenceResult(
        wav_path="/tmp/test/speaker_ref.wav",
        reference_text="Hello world",
    )


@pytest.fixture
def mock_words():
    return [
        WordTimestamp(word="Hello", start=0.0, end=0.5),
        WordTimestamp(word="world", start=0.6, end=1.0),
        WordTimestamp(word="how", start=1.5, end=1.8),
        WordTimestamp(word="are", start=1.9, end=2.1),
        WordTimestamp(word="you", start=2.2, end=2.5),
    ]
