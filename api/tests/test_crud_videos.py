import pytest
from unittest.mock import AsyncMock, patch, call


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


class TestUpdateVideoAfterDub:
    @pytest.mark.asyncio
    async def test_sets_dubbed_url_and_media_fields(self):
        with patch("app.repositories.videos.videos_collection") as mock_col:
            mock_col.update_one = AsyncMock()
            from app.repositories.videos import update_video_after_dub
            await update_video_after_dub("vid-1", DUB_RESULT)

        # First call: $set
        first_call = mock_col.update_one.call_args_list[0]
        set_fields = first_call[0][1]["$set"]
        assert set_fields["dubbed_url"] == "http://s3/dubbed.mp4"
        assert set_fields["vocals_url"] == "http://s3/vocals.wav"
        assert set_fields["no_vocals_url"] == "http://s3/no_vocals.wav"
        assert set_fields["transcription"] == "[0.00s - 2.50s] Hello\n"
        assert set_fields["transcript_segments"] == [{"start": 0.0, "end": 2.5, "text": "Hello"}]

    @pytest.mark.asyncio
    async def test_sets_detected_language_when_present(self):
        with patch("app.repositories.videos.videos_collection") as mock_col:
            mock_col.update_one = AsyncMock()
            from app.repositories.videos import update_video_after_dub
            await update_video_after_dub("vid-1", DUB_RESULT)

        set_fields = mock_col.update_one.call_args_list[0][0][1]["$set"]
        assert set_fields["detected_language"] == "es"

    @pytest.mark.asyncio
    async def test_omits_language_when_absent(self):
        result = {**DUB_RESULT, "detected_language": None}
        with patch("app.repositories.videos.videos_collection") as mock_col:
            mock_col.update_one = AsyncMock()
            from app.repositories.videos import update_video_after_dub
            await update_video_after_dub("vid-1", result)

        set_fields = mock_col.update_one.call_args_list[0][0][1]["$set"]
        assert "detected_language" not in set_fields

    @pytest.mark.asyncio
    async def test_pushes_dubbed_version_entry(self):
        with patch("app.repositories.videos.videos_collection") as mock_col:
            mock_col.update_one = AsyncMock()
            from app.repositories.videos import update_video_after_dub
            await update_video_after_dub("vid-1", DUB_RESULT)

        # Second call: conditional $push
        second_call = mock_col.update_one.call_args_list[1]
        push_doc = second_call[0][1]["$push"]["dubbed_versions"]
        assert push_doc["job_id"] == "job-1"
        assert push_doc["url"] == "http://s3/dubbed.mp4"

    @pytest.mark.asyncio
    async def test_push_is_conditional_on_job_id_absence(self):
        with patch("app.repositories.videos.videos_collection") as mock_col:
            mock_col.update_one = AsyncMock()
            from app.repositories.videos import update_video_after_dub
            await update_video_after_dub("vid-1", DUB_RESULT)

        second_call_filter = mock_col.update_one.call_args_list[1][0][0]
        # Filter must exclude documents where dubbed_versions already contains job-1
        assert "dubbed_versions" in second_call_filter
        assert "$not" in second_call_filter["dubbed_versions"]

    @pytest.mark.asyncio
    async def test_sets_duration_seconds(self):
        with patch("app.repositories.videos.videos_collection") as mock_col:
            mock_col.update_one = AsyncMock()
            from app.repositories.videos import update_video_after_dub
            await update_video_after_dub("vid-1", DUB_RESULT)

        set_fields = mock_col.update_one.call_args_list[0][0][1]["$set"]
        assert set_fields["duration_seconds"] == 30.0


class TestUpdateVideoAfterTranscribe:
    @pytest.mark.asyncio
    async def test_sets_transcription_fields(self):
        with patch("app.repositories.videos.videos_collection") as mock_col:
            mock_col.update_one = AsyncMock()
            from app.repositories.videos import update_video_after_transcribe
            await update_video_after_transcribe("vid-1", TRANSCRIBE_RESULT)

        set_fields = mock_col.update_one.call_args[0][1]["$set"]
        assert set_fields["transcript_url"] == "http://s3/transcript.txt"
        assert set_fields["transcription"] == "[0.00s - 2.50s] Hello\n"
        assert set_fields["transcript_segments"] == [{"start": 0.0, "end": 2.5, "text": "Hello"}]

    @pytest.mark.asyncio
    async def test_sets_detected_language_when_present(self):
        with patch("app.repositories.videos.videos_collection") as mock_col:
            mock_col.update_one = AsyncMock()
            from app.repositories.videos import update_video_after_transcribe
            await update_video_after_transcribe("vid-1", TRANSCRIBE_RESULT)

        set_fields = mock_col.update_one.call_args[0][1]["$set"]
        assert set_fields["detected_language"] == "es"

    @pytest.mark.asyncio
    async def test_omits_language_when_absent(self):
        result = {**TRANSCRIBE_RESULT, "detected_language": None}
        with patch("app.repositories.videos.videos_collection") as mock_col:
            mock_col.update_one = AsyncMock()
            from app.repositories.videos import update_video_after_transcribe
            await update_video_after_transcribe("vid-1", result)

        set_fields = mock_col.update_one.call_args[0][1]["$set"]
        assert "detected_language" not in set_fields

    @pytest.mark.asyncio
    async def test_sets_duration_seconds(self):
        with patch("app.repositories.videos.videos_collection") as mock_col:
            mock_col.update_one = AsyncMock()
            from app.repositories.videos import update_video_after_transcribe
            await update_video_after_transcribe("vid-1", TRANSCRIBE_RESULT)

        set_fields = mock_col.update_one.call_args[0][1]["$set"]
        assert set_fields["duration_seconds"] == 30.0

    @pytest.mark.asyncio
    async def test_omits_duration_when_absent(self):
        result = {**TRANSCRIBE_RESULT, "duration_seconds": None}
        with patch("app.repositories.videos.videos_collection") as mock_col:
            mock_col.update_one = AsyncMock()
            from app.repositories.videos import update_video_after_transcribe
            await update_video_after_transcribe("vid-1", result)

        set_fields = mock_col.update_one.call_args[0][1]["$set"]
        assert "duration_seconds" not in set_fields

    @pytest.mark.asyncio
    async def test_calls_update_once(self):
        with patch("app.repositories.videos.videos_collection") as mock_col:
            mock_col.update_one = AsyncMock()
            from app.repositories.videos import update_video_after_transcribe
            await update_video_after_transcribe("vid-1", TRANSCRIBE_RESULT)

        assert mock_col.update_one.call_count == 1
