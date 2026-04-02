import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


DUB_RESULT = {
    "status": "completed",
    "dubbed_url": "http://s3/dubbed.mp4",
    "transcript_url": "http://s3/transcript.txt",
    "vocals_url": "http://s3/vocals.wav",
    "no_vocals_url": "http://s3/no_vocals.wav",
    "video_id": "vid-1",
    "job_id": "job-1",
    "transcription": "[0.00s - 2.50s] Hello\n",
    "transcript_segments": [{"start": 0.0, "end": 2.5, "text": "Hello"}],
    "detected_language": "es",
    "duration_seconds": 30.0,
}

TRANSCRIBE_RESULT = {
    "status": "completed",
    "video_id": "vid-1",
    "transcript_url": "http://s3/transcript.txt",
    "transcription": "[0.00s - 2.50s] Hello\n",
    "transcript_segments": [{"start": 0.0, "end": 2.5, "text": "Hello"}],
    "detected_language": "es",
    "duration_seconds": 30.0,
}


def make_mock_session(row=None):
    """Return (mock_session_local, mock_session) with scalar_one_or_none returning row."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    mock_begin = AsyncMock()
    mock_begin.__aenter__ = AsyncMock(return_value=None)
    mock_begin.__aexit__ = AsyncMock(return_value=False)
    mock_session.begin = MagicMock(return_value=mock_begin)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = row
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_session_local = MagicMock(return_value=mock_ctx)
    return mock_session_local, mock_session


def make_video_row(dubbed_versions=None, **kwargs):
    """Create a mock Video ORM row with sensible defaults."""
    row = MagicMock()
    row.dubbed_versions = dubbed_versions if dubbed_versions is not None else []
    row.dubbed_url = None
    row.vocals_url = None
    row.no_vocals_url = None
    row.transcript_url = None
    row.transcription = None
    row.transcript_segments = None
    row.detected_language = None
    row.duration_seconds = None
    row.updated_at = datetime.now(timezone.utc)
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


class TestUpdateVideoAfterDub:
    async def test_sets_dubbed_url_and_media_fields(self):
        row = make_video_row()
        mock_session_local, _ = make_mock_session(row)
        with patch("app.repositories.videos.AsyncSessionLocal", mock_session_local):
            from app.repositories.videos import update_video_after_dub
            await update_video_after_dub("vid-1", DUB_RESULT)

        assert row.dubbed_url == "http://s3/dubbed.mp4"
        assert row.vocals_url == "http://s3/vocals.wav"
        assert row.no_vocals_url == "http://s3/no_vocals.wav"
        assert row.transcription == "[0.00s - 2.50s] Hello\n"
        assert row.transcript_segments == [{"start": 0.0, "end": 2.5, "text": "Hello"}]

    async def test_sets_detected_language_when_present(self):
        row = make_video_row()
        mock_session_local, _ = make_mock_session(row)
        with patch("app.repositories.videos.AsyncSessionLocal", mock_session_local):
            from app.repositories.videos import update_video_after_dub
            await update_video_after_dub("vid-1", DUB_RESULT)

        assert row.detected_language == "es"

    async def test_omits_language_when_absent(self):
        row = make_video_row()
        mock_session_local, _ = make_mock_session(row)
        result = {**DUB_RESULT, "detected_language": None}
        with patch("app.repositories.videos.AsyncSessionLocal", mock_session_local):
            from app.repositories.videos import update_video_after_dub
            await update_video_after_dub("vid-1", result)

        assert row.detected_language is None

    async def test_pushes_dubbed_version_entry(self):
        row = make_video_row(dubbed_versions=[])
        mock_session_local, _ = make_mock_session(row)
        with patch("app.repositories.videos.AsyncSessionLocal", mock_session_local):
            from app.repositories.videos import update_video_after_dub
            await update_video_after_dub("vid-1", DUB_RESULT)

        assert len(row.dubbed_versions) == 1
        assert row.dubbed_versions[0]["job_id"] == "job-1"
        assert row.dubbed_versions[0]["url"] == "http://s3/dubbed.mp4"

    async def test_push_is_idempotent(self):
        """Second call with same job_id must not add a second entry."""
        existing = [{"job_id": "job-1", "url": "http://s3/dubbed.mp4", "created_at": "2024-01-01T00:00:00+00:00"}]
        row = make_video_row(dubbed_versions=existing)
        mock_session_local, _ = make_mock_session(row)
        with patch("app.repositories.videos.AsyncSessionLocal", mock_session_local):
            from app.repositories.videos import update_video_after_dub
            await update_video_after_dub("vid-1", DUB_RESULT)

        assert len(row.dubbed_versions) == 1

    async def test_sets_duration_seconds(self):
        row = make_video_row()
        mock_session_local, _ = make_mock_session(row)
        with patch("app.repositories.videos.AsyncSessionLocal", mock_session_local):
            from app.repositories.videos import update_video_after_dub
            await update_video_after_dub("vid-1", DUB_RESULT)

        assert row.duration_seconds == 30.0


class TestUpdateVideoAfterTranscribe:
    async def test_sets_transcription_fields(self):
        row = make_video_row()
        mock_session_local, _ = make_mock_session(row)
        with patch("app.repositories.videos.AsyncSessionLocal", mock_session_local):
            from app.repositories.videos import update_video_after_transcribe
            await update_video_after_transcribe("vid-1", TRANSCRIBE_RESULT)

        assert row.transcript_url == "http://s3/transcript.txt"
        assert row.transcription == "[0.00s - 2.50s] Hello\n"
        assert row.transcript_segments == [{"start": 0.0, "end": 2.5, "text": "Hello"}]

    async def test_sets_detected_language_when_present(self):
        row = make_video_row()
        mock_session_local, _ = make_mock_session(row)
        with patch("app.repositories.videos.AsyncSessionLocal", mock_session_local):
            from app.repositories.videos import update_video_after_transcribe
            await update_video_after_transcribe("vid-1", TRANSCRIBE_RESULT)

        assert row.detected_language == "es"

    async def test_omits_language_when_absent(self):
        row = make_video_row()
        mock_session_local, _ = make_mock_session(row)
        result = {**TRANSCRIBE_RESULT, "detected_language": None}
        with patch("app.repositories.videos.AsyncSessionLocal", mock_session_local):
            from app.repositories.videos import update_video_after_transcribe
            await update_video_after_transcribe("vid-1", result)

        assert row.detected_language is None

    async def test_sets_duration_seconds(self):
        row = make_video_row()
        mock_session_local, _ = make_mock_session(row)
        with patch("app.repositories.videos.AsyncSessionLocal", mock_session_local):
            from app.repositories.videos import update_video_after_transcribe
            await update_video_after_transcribe("vid-1", TRANSCRIBE_RESULT)

        assert row.duration_seconds == 30.0

    async def test_omits_duration_when_absent(self):
        row = make_video_row(duration_seconds=None)
        mock_session_local, _ = make_mock_session(row)
        result = {**TRANSCRIBE_RESULT, "duration_seconds": None}
        with patch("app.repositories.videos.AsyncSessionLocal", mock_session_local):
            from app.repositories.videos import update_video_after_transcribe
            await update_video_after_transcribe("vid-1", result)

        assert row.duration_seconds is None
