import pytest
from unittest.mock import AsyncMock, patch


DUB_RESULT = {
    "status": "completed",
    "dubbed_url": "http://minio:9000/bucket/proj/dubbed.mp4",
    "transcript_url": "http://minio:9000/bucket/proj/transcript.txt",
    "vocals_url": "http://minio:9000/bucket/proj/vocals.wav",
    "no_vocals_url": "http://minio:9000/bucket/proj/no_vocals.wav",
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
    "transcript_url": "http://minio:9000/bucket/proj/transcript.txt",
    "transcription": "[0.00s - 2.50s] Hello\n",
    "transcript_segments": [{"start": 0.0, "end": 2.5, "text": "Hello"}],
    "detected_language": "es",
    "duration_seconds": 30.0,
}

TTS_RESULT = {
    "audio_url": "http://minio:9000/bucket/tts/job.wav",
    "format": "wav",
}


class TestPersistJobResult:
    @pytest.mark.asyncio
    async def test_calls_update_video_after_dub_for_dub_result(self):
        with patch("app.services.jobs.videos_repo") as mock_repo:
            mock_repo.update_video_after_dub = AsyncMock()
            mock_repo.update_video_after_transcribe = AsyncMock()
            from app.services.jobs import persist_job_result
            await persist_job_result(DUB_RESULT)

        mock_repo.update_video_after_dub.assert_called_once_with("vid-1", DUB_RESULT)
        mock_repo.update_video_after_transcribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_update_video_after_transcribe_for_transcribe_result(self):
        with patch("app.services.jobs.videos_repo") as mock_repo:
            mock_repo.update_video_after_dub = AsyncMock()
            mock_repo.update_video_after_transcribe = AsyncMock()
            from app.services.jobs import persist_job_result
            await persist_job_result(TRANSCRIBE_RESULT)

        mock_repo.update_video_after_transcribe.assert_called_once_with("vid-1", TRANSCRIBE_RESULT)
        mock_repo.update_video_after_dub.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_db_for_tts_result(self):
        with patch("app.services.jobs.videos_repo") as mock_repo:
            mock_repo.update_video_after_dub = AsyncMock()
            mock_repo.update_video_after_transcribe = AsyncMock()
            from app.services.jobs import persist_job_result
            await persist_job_result(TTS_RESULT)

        mock_repo.update_video_after_dub.assert_not_called()
        mock_repo.update_video_after_transcribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_db_for_empty_result(self):
        with patch("app.services.jobs.videos_repo") as mock_repo:
            mock_repo.update_video_after_dub = AsyncMock()
            mock_repo.update_video_after_transcribe = AsyncMock()
            from app.services.jobs import persist_job_result
            await persist_job_result({})

        mock_repo.update_video_after_dub.assert_not_called()
        mock_repo.update_video_after_transcribe.assert_not_called()


class TestEnrichResult:
    @pytest.mark.asyncio
    async def test_rewrites_dubbed_url(self):
        with patch("app.services.jobs.storage") as mock_storage:
            mock_storage.generate_presigned_url.return_value = (
                "http://minio:9000/bucket/proj/dubbed.mp4?sig=abc"
            )
            from app.services.jobs import enrich_result
            result = await enrich_result(DUB_RESULT)

        assert "sig=abc" in result["dubbed_url"]

    @pytest.mark.asyncio
    async def test_includes_segment_count(self):
        with patch("app.services.jobs.storage") as mock_storage:
            mock_storage.generate_presigned_url.return_value = "http://minio:9000/x?sig=x"
            from app.services.jobs import enrich_result
            result = await enrich_result(DUB_RESULT)

        assert result["segment_count"] == 1

    @pytest.mark.asyncio
    async def test_preserves_transcription_from_result(self):
        with patch("app.services.jobs.storage") as mock_storage:
            mock_storage.generate_presigned_url.return_value = "http://minio:9000/x?sig=x"
            from app.services.jobs import enrich_result
            result = await enrich_result(DUB_RESULT)

        assert result["transcription"] == "[0.00s - 2.50s] Hello\n"

    @pytest.mark.asyncio
    async def test_does_not_read_from_mongodb(self):
        """enrich_result must not touch MongoDB — transcription data comes from the result dict."""
        with (
            patch("app.services.jobs.storage") as mock_storage,
            patch("app.services.jobs.videos_repo") as mock_repo,
        ):
            mock_storage.generate_presigned_url.return_value = "http://minio:9000/x?sig=x"
            from app.services.jobs import enrich_result
            await enrich_result(DUB_RESULT)

        mock_repo.get_video.assert_not_called()

    @pytest.mark.asyncio
    async def test_rewrites_audio_url_for_tts_result(self):
        with patch("app.services.jobs.storage") as mock_storage:
            mock_storage.generate_presigned_url.return_value = (
                "http://minio:9000/bucket/tts/job.wav?sig=tts"
            )
            from app.services.jobs import enrich_result
            result = await enrich_result(TTS_RESULT)

        assert "sig=tts" in result["audio_url"]

    @pytest.mark.asyncio
    async def test_omits_segment_count_when_no_segments(self):
        raw = {"video_id": "vid-1", "dubbed_url": "http://s3/x"}
        with patch("app.services.jobs.storage") as mock_storage:
            mock_storage.generate_presigned_url.return_value = "http://s3/x?sig=x"
            from app.services.jobs import enrich_result
            result = await enrich_result(raw)

        assert "segment_count" not in result
