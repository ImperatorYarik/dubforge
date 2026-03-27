import pytest
from unittest.mock import MagicMock, patch
from app.models.job import JobContext, TranscribeJobResult
from app.models.audio import SeparationResult
from app.models.segment import TranscriptSegment


MOCK_SEPARATION = SeparationResult(
    vocals_path="/tmp/test/vocals.wav",
    no_vocals_path="/tmp/test/no_vocals.wav",
)

MOCK_SEGMENTS = [
    TranscriptSegment(start=0.0, end=5.0, text="Hello world"),
    TranscriptSegment(start=5.5, end=10.0, text="How are you"),
]


@pytest.fixture
def pipeline():
    from app.pipelines.transcribe_pipeline import transcribe_video
    return transcribe_video


@pytest.fixture
def ctx(tmp_path):
    return JobContext(
        project_id="proj1",
        video_id="vid1",
        input_url="http://minio:9000/bucket/proj1/video.mp4",
        job_id="job1",
        tmp_dir=str(tmp_path),
    )


@pytest.fixture
def progress():
    return MagicMock()


class TestTranscribePipelineExecute:
    def test_returns_transcribe_job_result(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.transcribe_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.transcribe_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.transcribe_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.transcribe_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.transcribe_pipeline.transcript_repository") as mock_transcript_repo,
            patch("app.pipelines.transcribe_pipeline.model_manager"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")
            mock_transcript_repo.save_transcription.return_value = "http://s3/transcript.txt"

            result = pipeline.execute(ctx, True, progress)

        assert isinstance(result, TranscribeJobResult)
        assert result.status == "completed"
        assert result.video_id == "vid1"
        assert result.transcript_url == "http://s3/transcript.txt"

    def test_result_includes_transcription_data(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.transcribe_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.transcribe_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.transcribe_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.transcribe_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.transcribe_pipeline.transcript_repository") as mock_transcript_repo,
            patch("app.pipelines.transcribe_pipeline.model_manager"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")
            mock_transcript_repo.save_transcription.return_value = "http://s3/t.txt"

            result = pipeline.execute(ctx, True, progress)

        assert result.detected_language == "en"
        assert result.duration_seconds == 10.0
        assert result.transcription is not None
        assert result.transcript_segments is not None
        assert len(result.transcript_segments) == 2

    def test_uses_cached_vocals_when_provided(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.transcribe_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.transcribe_pipeline.download_file_to_disk") as mock_dl,
            patch("app.pipelines.transcribe_pipeline.separate_sources") as mock_separate,
            patch("app.pipelines.transcribe_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.transcribe_pipeline.transcript_repository") as mock_transcript_repo,
            patch("app.pipelines.transcribe_pipeline.model_manager"),
        ):
            mock_audio_repo.download_cached_separation.return_value = MOCK_SEPARATION
            mock_transcript_repo.save_transcription.return_value = "http://s3/t.txt"

            pipeline.execute(
                ctx, True, progress,
                vocals_url="http://s3/v.wav", no_vocals_url="http://s3/nv.wav",
            )

        mock_dl.assert_not_called()
        mock_separate.assert_not_called()

    def test_cached_vocals_url_passed_to_audio_repository(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.transcribe_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.transcribe_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.transcribe_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.transcribe_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.transcribe_pipeline.transcript_repository") as mock_transcript_repo,
            patch("app.pipelines.transcribe_pipeline.model_manager"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")
            mock_transcript_repo.save_transcription.return_value = "http://s3/t.txt"

            pipeline.execute(
                ctx, True, progress,
                vocals_url="http://s3/existing_v.wav", no_vocals_url="http://s3/existing_nv.wav",
            )

        call_args = mock_audio_repo.download_cached_separation.call_args[0]
        assert call_args[0] == "http://s3/existing_v.wav"
        assert call_args[1] == "http://s3/existing_nv.wav"

    def test_skip_demucs_extracts_audio_without_separation(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.transcribe_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.transcribe_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.transcribe_pipeline.separate_sources") as mock_separate,
            patch("app.pipelines.transcribe_pipeline._extract_audio") as mock_extract,
            patch("app.pipelines.transcribe_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.transcribe_pipeline.transcript_repository") as mock_transcript_repo,
            patch("app.pipelines.transcribe_pipeline.model_manager"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_transcript_repo.save_transcription.return_value = "http://s3/t.txt"

            pipeline.execute(ctx, True, progress, skip_demucs=True)

        mock_separate.assert_not_called()
        mock_extract.assert_called_once()

    def test_demucs_called_when_not_skipped(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.transcribe_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.transcribe_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.transcribe_pipeline.separate_sources", return_value=MOCK_SEPARATION) as mock_separate,
            patch("app.pipelines.transcribe_pipeline._extract_audio") as mock_extract,
            patch("app.pipelines.transcribe_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.transcribe_pipeline.transcript_repository") as mock_transcript_repo,
            patch("app.pipelines.transcribe_pipeline.model_manager"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")
            mock_transcript_repo.save_transcription.return_value = "http://s3/t.txt"

            pipeline.execute(ctx, True, progress, skip_demucs=False)

        mock_separate.assert_called_once()
        mock_extract.assert_not_called()

    def test_download_failure_raises(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.transcribe_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.transcribe_pipeline.download_file_to_disk", return_value=False),
            patch("app.pipelines.transcribe_pipeline.model_manager"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None

            with pytest.raises(RuntimeError, match="Download failed"):
                pipeline.execute(ctx, True, progress)

    def test_calls_transcript_repository_save(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.transcribe_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.transcribe_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.transcribe_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.transcribe_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.transcribe_pipeline.transcript_repository") as mock_transcript_repo,
            patch("app.pipelines.transcribe_pipeline.model_manager"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")
            mock_transcript_repo.save_transcription.return_value = "http://s3/t.txt"

            pipeline.execute(ctx, True, progress)

        mock_transcript_repo.save_transcription.assert_called_once()
        args = mock_transcript_repo.save_transcription.call_args[0]
        assert args[0] == "proj1"
        assert args[1] == "job1"

    def test_passes_model_name_to_transcribe_audio(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.transcribe_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.transcribe_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.transcribe_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.transcribe_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)) as mock_transcribe,
            patch("app.pipelines.transcribe_pipeline.transcript_repository") as mock_transcript_repo,
            patch("app.pipelines.transcribe_pipeline.model_manager"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")
            mock_transcript_repo.save_transcription.return_value = "http://s3/t.txt"

            pipeline.execute(ctx, True, progress, model="large-v2")

        _, kwargs = mock_transcribe.call_args
        assert kwargs.get("model_name") == "large-v2"

    def test_passes_language_to_transcribe_audio(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.transcribe_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.transcribe_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.transcribe_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.transcribe_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)) as mock_transcribe,
            patch("app.pipelines.transcribe_pipeline.transcript_repository") as mock_transcript_repo,
            patch("app.pipelines.transcribe_pipeline.model_manager"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")
            mock_transcript_repo.save_transcription.return_value = "http://s3/t.txt"

            pipeline.execute(ctx, False, progress, language="es")

        _, kwargs = mock_transcribe.call_args
        assert kwargs.get("language") == "es"
