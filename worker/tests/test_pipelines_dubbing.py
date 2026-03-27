import pytest
from unittest.mock import MagicMock, patch
from app.models.job import JobContext, DubJobResult
from app.models.audio import SeparationResult, VoiceReferenceResult
from app.models.segment import TranscriptSegment


MOCK_SEPARATION = SeparationResult(
    vocals_path="/tmp/test/vocals.wav",
    no_vocals_path="/tmp/test/no_vocals.wav",
)

MOCK_SEGMENTS = [
    TranscriptSegment(start=0.0, end=5.0, text="Hello world"),
]

MOCK_REF = VoiceReferenceResult(
    wav_path="/tmp/test/speaker_ref.wav",
    reference_text="Hello world",
)


@pytest.fixture
def pipeline():
    from app.pipelines.dubbing_pipeline import dub_video
    return dub_video


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


def _full_patch(extra_patches=None):
    """Return context managers for all heavy dependencies."""
    patches = [
        patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=True),
        patch("app.pipelines.dubbing_pipeline.audio_repository"),
        patch("app.pipelines.dubbing_pipeline.separate_sources", return_value=MOCK_SEPARATION),
        patch("app.pipelines.dubbing_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
        patch("app.pipelines.dubbing_pipeline.extract_reference_wav", return_value=MOCK_REF),
        patch("app.pipelines.dubbing_pipeline.model_manager"),
        patch("app.pipelines.dubbing_pipeline.synthesize", return_value=True),
        patch("app.pipelines.dubbing_pipeline.stretch_clip", return_value=True),
        patch("app.pipelines.dubbing_pipeline.build_dubbed_audio", return_value=True),
        patch("app.pipelines.dubbing_pipeline.mux_audio_into_video", return_value=True),
        patch("app.pipelines.dubbing_pipeline.upload_to_s3", return_value="http://s3/file"),
    ]
    return patches


class TestDubbingPipelineExecute:
    def test_returns_dub_job_result(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.dubbing_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.dubbing_pipeline.extract_reference_wav", return_value=MOCK_REF),
            patch("app.pipelines.dubbing_pipeline.model_manager"),
            patch("app.pipelines.dubbing_pipeline.synthesize", return_value=True),
            patch("app.pipelines.dubbing_pipeline.stretch_clip", return_value=True),
            patch("app.pipelines.dubbing_pipeline.build_dubbed_audio", return_value=True),
            patch("app.pipelines.dubbing_pipeline.mux_audio_into_video", return_value=True),
            patch("app.pipelines.dubbing_pipeline.upload_to_s3", return_value="http://s3/file"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")

            result = pipeline.execute(ctx, progress, skip_transcription=False)

        assert isinstance(result, DubJobResult)
        assert result.status == "completed"
        assert result.video_id == "vid1"

    def test_result_includes_job_id(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.dubbing_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.dubbing_pipeline.extract_reference_wav", return_value=MOCK_REF),
            patch("app.pipelines.dubbing_pipeline.model_manager"),
            patch("app.pipelines.dubbing_pipeline.synthesize", return_value=True),
            patch("app.pipelines.dubbing_pipeline.stretch_clip", return_value=True),
            patch("app.pipelines.dubbing_pipeline.build_dubbed_audio", return_value=True),
            patch("app.pipelines.dubbing_pipeline.mux_audio_into_video", return_value=True),
            patch("app.pipelines.dubbing_pipeline.upload_to_s3", return_value="http://s3/file"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")

            result = pipeline.execute(ctx, progress, skip_transcription=False)

        assert result.job_id == "job1"

    def test_result_includes_transcription_data(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.dubbing_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.dubbing_pipeline.extract_reference_wav", return_value=MOCK_REF),
            patch("app.pipelines.dubbing_pipeline.model_manager"),
            patch("app.pipelines.dubbing_pipeline.synthesize", return_value=True),
            patch("app.pipelines.dubbing_pipeline.stretch_clip", return_value=True),
            patch("app.pipelines.dubbing_pipeline.build_dubbed_audio", return_value=True),
            patch("app.pipelines.dubbing_pipeline.mux_audio_into_video", return_value=True),
            patch("app.pipelines.dubbing_pipeline.upload_to_s3", return_value="http://s3/file"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")

            result = pipeline.execute(ctx, progress, skip_transcription=False)

        assert result.detected_language == "en"
        assert result.duration_seconds == 10.0
        assert result.transcription is not None
        assert result.transcript_segments is not None

    def test_uses_cached_vocals_when_provided(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.separate_sources") as mock_separate,
            patch("app.pipelines.dubbing_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.dubbing_pipeline.extract_reference_wav", return_value=MOCK_REF),
            patch("app.pipelines.dubbing_pipeline.model_manager"),
            patch("app.pipelines.dubbing_pipeline.synthesize", return_value=True),
            patch("app.pipelines.dubbing_pipeline.stretch_clip", return_value=True),
            patch("app.pipelines.dubbing_pipeline.build_dubbed_audio", return_value=True),
            patch("app.pipelines.dubbing_pipeline.mux_audio_into_video", return_value=True),
            patch("app.pipelines.dubbing_pipeline.upload_to_s3", return_value="http://s3/file"),
        ):
            mock_audio_repo.download_cached_separation.return_value = MOCK_SEPARATION

            pipeline.execute(
                ctx, progress, skip_transcription=False,
                vocals_url="http://s3/v.wav", no_vocals_url="http://s3/nv.wav",
            )

        mock_separate.assert_not_called()

    def test_cached_vocals_url_passed_to_audio_repository(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.dubbing_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.dubbing_pipeline.extract_reference_wav", return_value=MOCK_REF),
            patch("app.pipelines.dubbing_pipeline.model_manager"),
            patch("app.pipelines.dubbing_pipeline.synthesize", return_value=True),
            patch("app.pipelines.dubbing_pipeline.stretch_clip", return_value=True),
            patch("app.pipelines.dubbing_pipeline.build_dubbed_audio", return_value=True),
            patch("app.pipelines.dubbing_pipeline.mux_audio_into_video", return_value=True),
            patch("app.pipelines.dubbing_pipeline.upload_to_s3", return_value="http://s3/file"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")

            pipeline.execute(
                ctx, progress, skip_transcription=False,
                vocals_url="http://s3/existing_v.wav", no_vocals_url="http://s3/existing_nv.wav",
            )

        call_args = mock_audio_repo.download_cached_separation.call_args[0]
        assert call_args[0] == "http://s3/existing_v.wav"
        assert call_args[1] == "http://s3/existing_nv.wav"

    def test_skip_transcription_uses_existing_segments(self, pipeline, ctx, progress):
        existing_segments = [{"start": 0.0, "end": 3.0, "text": "Existing"}]

        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.dubbing_pipeline.transcribe_audio") as mock_transcribe,
            patch("app.pipelines.dubbing_pipeline.extract_reference_wav", return_value=MOCK_REF),
            patch("app.pipelines.dubbing_pipeline.model_manager"),
            patch("app.pipelines.dubbing_pipeline.synthesize", return_value=True),
            patch("app.pipelines.dubbing_pipeline.stretch_clip", return_value=True),
            patch("app.pipelines.dubbing_pipeline.build_dubbed_audio", return_value=True),
            patch("app.pipelines.dubbing_pipeline.mux_audio_into_video", return_value=True),
            patch("app.pipelines.dubbing_pipeline.upload_to_s3", return_value="http://s3/file"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")

            pipeline.execute(
                ctx, progress, skip_transcription=True,
                existing_segments=existing_segments,
                existing_transcription="[0.00s - 3.00s] Existing\n",
            )

        mock_transcribe.assert_not_called()

    def test_skip_transcription_preserves_existing_language_and_duration(self, pipeline, ctx, progress):
        existing_segments = [{"start": 0.0, "end": 3.0, "text": "Existing"}]

        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.dubbing_pipeline.transcribe_audio"),
            patch("app.pipelines.dubbing_pipeline.extract_reference_wav", return_value=MOCK_REF),
            patch("app.pipelines.dubbing_pipeline.model_manager"),
            patch("app.pipelines.dubbing_pipeline.synthesize", return_value=True),
            patch("app.pipelines.dubbing_pipeline.stretch_clip", return_value=True),
            patch("app.pipelines.dubbing_pipeline.build_dubbed_audio", return_value=True),
            patch("app.pipelines.dubbing_pipeline.mux_audio_into_video", return_value=True),
            patch("app.pipelines.dubbing_pipeline.upload_to_s3", return_value="http://s3/file"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")

            result = pipeline.execute(
                ctx, progress, skip_transcription=True,
                existing_segments=existing_segments,
                existing_transcription="[0.00s - 3.00s] Existing\n",
                existing_detected_language="es",
                existing_duration_seconds=42.0,
            )

        assert result.detected_language == "es"
        assert result.duration_seconds == 42.0

    def test_skip_transcription_raises_when_no_existing(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.dubbing_pipeline.model_manager"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")

            with pytest.raises(RuntimeError, match="No parseable segments"):
                pipeline.execute(ctx, progress, skip_transcription=True)

    def test_download_failure_raises(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=False),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.model_manager"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None

            with pytest.raises(RuntimeError, match="Download failed"):
                pipeline.execute(ctx, progress, skip_transcription=False)

    def test_mix_failure_raises(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.dubbing_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.dubbing_pipeline.extract_reference_wav", return_value=MOCK_REF),
            patch("app.pipelines.dubbing_pipeline.model_manager"),
            patch("app.pipelines.dubbing_pipeline.synthesize", return_value=True),
            patch("app.pipelines.dubbing_pipeline.stretch_clip", return_value=True),
            patch("app.pipelines.dubbing_pipeline.build_dubbed_audio", return_value=False),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")

            with pytest.raises(RuntimeError, match="Audio mix failed"):
                pipeline.execute(ctx, progress, skip_transcription=False)

    def test_mux_failure_raises(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.dubbing_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.dubbing_pipeline.extract_reference_wav", return_value=MOCK_REF),
            patch("app.pipelines.dubbing_pipeline.model_manager"),
            patch("app.pipelines.dubbing_pipeline.synthesize", return_value=True),
            patch("app.pipelines.dubbing_pipeline.stretch_clip", return_value=True),
            patch("app.pipelines.dubbing_pipeline.build_dubbed_audio", return_value=True),
            patch("app.pipelines.dubbing_pipeline.mux_audio_into_video", return_value=False),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")

            with pytest.raises(RuntimeError, match="Mux failed"):
                pipeline.execute(ctx, progress, skip_transcription=False)

    def test_progress_updated_at_key_steps(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.dubbing_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.dubbing_pipeline.extract_reference_wav", return_value=MOCK_REF),
            patch("app.pipelines.dubbing_pipeline.model_manager"),
            patch("app.pipelines.dubbing_pipeline.synthesize", return_value=True),
            patch("app.pipelines.dubbing_pipeline.stretch_clip", return_value=True),
            patch("app.pipelines.dubbing_pipeline.build_dubbed_audio", return_value=True),
            patch("app.pipelines.dubbing_pipeline.mux_audio_into_video", return_value=True),
            patch("app.pipelines.dubbing_pipeline.upload_to_s3", return_value="http://s3/file"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")

            pipeline.execute(ctx, progress, skip_transcription=False)

        assert progress.update.call_count >= 5

    def test_uploads_dubbed_video_to_correct_s3_key(self, pipeline, ctx, progress):
        uploaded_keys = []

        def track_upload(path, key):
            uploaded_keys.append(key)
            return f"http://s3/{key}"

        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.dubbing_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.dubbing_pipeline.extract_reference_wav", return_value=MOCK_REF),
            patch("app.pipelines.dubbing_pipeline.model_manager"),
            patch("app.pipelines.dubbing_pipeline.synthesize", return_value=True),
            patch("app.pipelines.dubbing_pipeline.stretch_clip", return_value=True),
            patch("app.pipelines.dubbing_pipeline.build_dubbed_audio", return_value=True),
            patch("app.pipelines.dubbing_pipeline.mux_audio_into_video", return_value=True),
            patch("app.pipelines.dubbing_pipeline.upload_to_s3", side_effect=track_upload),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")

            pipeline.execute(ctx, progress, skip_transcription=False)

        dubbed_key = next((k for k in uploaded_keys if k.startswith("proj1/dubbed_")), None)
        assert dubbed_key is not None
        assert dubbed_key.endswith(".mp4")

    def test_result_uses_vocals_urls_from_separation(self, pipeline, ctx, progress):
        """Vocals URLs in result should come from save_separation, not a second upload."""
        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.dubbing_pipeline.transcribe_audio", return_value=(MOCK_SEGMENTS, "en", 10.0)),
            patch("app.pipelines.dubbing_pipeline.extract_reference_wav", return_value=MOCK_REF),
            patch("app.pipelines.dubbing_pipeline.model_manager"),
            patch("app.pipelines.dubbing_pipeline.synthesize", return_value=True),
            patch("app.pipelines.dubbing_pipeline.stretch_clip", return_value=True),
            patch("app.pipelines.dubbing_pipeline.build_dubbed_audio", return_value=True),
            patch("app.pipelines.dubbing_pipeline.mux_audio_into_video", return_value=True),
            patch("app.pipelines.dubbing_pipeline.upload_to_s3", return_value="http://s3/other"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = (
                "http://s3/vocals_from_sep.wav",
                "http://s3/no_vocals_from_sep.wav",
            )

            result = pipeline.execute(ctx, progress, skip_transcription=False)

        assert result.vocals_url == "http://s3/vocals_from_sep.wav"
        assert result.no_vocals_url == "http://s3/no_vocals_from_sep.wav"
