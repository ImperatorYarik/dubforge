import pytest
from unittest.mock import MagicMock
from app.models.job import JobContext
from app.models.audio import SeparationResult, VoiceReferenceResult
from app.models.segment import TranscriptSegment, WordTimestamp


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
