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


def _all_patches(extra=None):
    defaults = {
        "app.pipelines.dubbing_pipeline.download_file_to_disk": {"return_value": True},
        "app.pipelines.dubbing_pipeline.audio_repository": {},
        "app.pipelines.dubbing_pipeline.separate_sources": {"return_value": MOCK_SEPARATION},
        "app.pipelines.dubbing_pipeline.transcribe_audio": {"return_value": (MOCK_SEGMENTS, "en", 10.0)},
        "app.pipelines.dubbing_pipeline.extract_reference_wav": {"return_value": MOCK_REF},
        "app.pipelines.dubbing_pipeline.model_manager": {},
        "app.pipelines.dubbing_pipeline.synthesize": {"return_value": True},
        "app.pipelines.dubbing_pipeline.stretch_clip": {"return_value": True},
        "app.pipelines.dubbing_pipeline.build_dubbed_audio": {"return_value": True},
        "app.pipelines.dubbing_pipeline.mux_audio_into_video": {"return_value": True},
        "app.pipelines.dubbing_pipeline.upload_to_s3": {"return_value": "http://s3/file"},
        "app.pipelines.dubbing_pipeline.videos_collection": {},
    }
    if extra:
        defaults.update(extra)
    return defaults


class TestDubbingPipelineExecute:
    def test_returns_dub_job_result(self, pipeline, ctx, progress, tmp_path):
        (tmp_path / "transcription.txt").write_text("[0.00s - 5.00s] Hello world\n")

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
            patch("app.pipelines.dubbing_pipeline.videos_collection"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")
            result = pipeline.execute(ctx, progress, skip_transcription=False)

        assert isinstance(result, DubJobResult)
        assert result.status == "completed"
        assert result.video_id == "vid1"

    def test_uses_cached_vocals_when_available(self, pipeline, ctx, progress, tmp_path):
        (tmp_path / "transcription.txt").write_text("[0.00s - 5.00s] Hello world\n")

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
            patch("app.pipelines.dubbing_pipeline.videos_collection"),
        ):
            mock_audio_repo.download_cached_separation.return_value = MOCK_SEPARATION
            pipeline.execute(ctx, progress, skip_transcription=False)

        mock_separate.assert_not_called()

    def test_skip_transcription_loads_existing(self, pipeline, ctx, progress, tmp_path):
        existing_segments = [TranscriptSegment(start=0.0, end=3.0, text="Existing")]
        (tmp_path / "transcription.txt").write_text("[0.00s - 3.00s] Existing\n")

        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.dubbing_pipeline.transcript_repository") as mock_transcript_repo,
            patch("app.pipelines.dubbing_pipeline.transcribe_audio") as mock_transcribe,
            patch("app.pipelines.dubbing_pipeline.extract_reference_wav", return_value=MOCK_REF),
            patch("app.pipelines.dubbing_pipeline.model_manager"),
            patch("app.pipelines.dubbing_pipeline.synthesize", return_value=True),
            patch("app.pipelines.dubbing_pipeline.stretch_clip", return_value=True),
            patch("app.pipelines.dubbing_pipeline.build_dubbed_audio", return_value=True),
            patch("app.pipelines.dubbing_pipeline.mux_audio_into_video", return_value=True),
            patch("app.pipelines.dubbing_pipeline.upload_to_s3", return_value="http://s3/file"),
            patch("app.pipelines.dubbing_pipeline.videos_collection"),
            patch("app.database.videos_collection") as mock_db_col,
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")
            mock_transcript_repo.get_existing.return_value = (existing_segments, "[0.00s - 3.00s] Existing\n")
            mock_db_col.find_one.return_value = {"detected_language": "en", "duration_seconds": 5.0}

            pipeline.execute(ctx, progress, skip_transcription=True)

        mock_transcribe.assert_not_called()
        mock_transcript_repo.get_existing.assert_called_once_with("vid1")

    def test_skip_transcription_raises_when_no_existing(self, pipeline, ctx, progress, tmp_path):
        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=True),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.separate_sources", return_value=MOCK_SEPARATION),
            patch("app.pipelines.dubbing_pipeline.transcript_repository") as mock_transcript_repo,
            patch("app.pipelines.dubbing_pipeline.model_manager"),
            patch("app.pipelines.dubbing_pipeline.videos_collection"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")
            mock_transcript_repo.get_existing.return_value = None

            with pytest.raises(RuntimeError, match="No parseable segments"):
                pipeline.execute(ctx, progress, skip_transcription=True)

    def test_download_failure_raises(self, pipeline, ctx, progress):
        with (
            patch("app.pipelines.dubbing_pipeline.download_file_to_disk", return_value=False),
            patch("app.pipelines.dubbing_pipeline.audio_repository") as mock_audio_repo,
            patch("app.pipelines.dubbing_pipeline.model_manager"),
            patch("app.pipelines.dubbing_pipeline.videos_collection"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None

            with pytest.raises(RuntimeError, match="Download failed"):
                pipeline.execute(ctx, progress, skip_transcription=False)

    def test_mix_failure_raises(self, pipeline, ctx, progress, tmp_path):
        (tmp_path / "transcription.txt").write_text("[0.00s - 5.00s] Hello world\n")

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
            patch("app.pipelines.dubbing_pipeline.videos_collection"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")

            with pytest.raises(RuntimeError, match="Audio mix failed"):
                pipeline.execute(ctx, progress, skip_transcription=False)

    def test_mux_failure_raises(self, pipeline, ctx, progress, tmp_path):
        (tmp_path / "transcription.txt").write_text("[0.00s - 5.00s] Hello world\n")

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
            patch("app.pipelines.dubbing_pipeline.videos_collection"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")

            with pytest.raises(RuntimeError, match="Mux failed"):
                pipeline.execute(ctx, progress, skip_transcription=False)

    def test_progress_updated_at_key_steps(self, pipeline, ctx, progress, tmp_path):
        (tmp_path / "transcription.txt").write_text("[0.00s - 5.00s] Hello world\n")

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
            patch("app.pipelines.dubbing_pipeline.videos_collection"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")
            pipeline.execute(ctx, progress, skip_transcription=False)

        assert progress.update.call_count >= 5

    def test_uploads_dubbed_video_to_correct_s3_key(self, pipeline, ctx, progress, tmp_path):
        (tmp_path / "transcription.txt").write_text("[0.00s - 5.00s] Hello world\n")
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
            patch("app.pipelines.dubbing_pipeline.videos_collection"),
        ):
            mock_audio_repo.download_cached_separation.return_value = None
            mock_audio_repo.save_separation.return_value = ("http://s3/v.wav", "http://s3/nv.wav")
            pipeline.execute(ctx, progress, skip_transcription=False)

        dubbed_key = next((k for k in uploaded_keys if k.startswith("proj1/dubbed_")), None)
        assert dubbed_key is not None
        assert dubbed_key.endswith(".mp4")
