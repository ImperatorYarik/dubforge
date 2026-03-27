import subprocess
import pytest
from unittest.mock import MagicMock, patch
from app.models.job import TtsJobResult


JOB_ID = "tts-job-123"


@pytest.fixture
def pipeline():
    from app.pipelines.tts_pipeline import generate_tts
    return generate_tts


@pytest.fixture
def progress():
    return MagicMock()


class TestTtsPipelineExecute:
    def test_returns_tts_job_result_wav(self, pipeline, progress, tmp_path):
        with (
            patch.object(pipeline, "_make_tmp", return_value=str(tmp_path)),
            patch.object(pipeline, "_cleanup_tmp"),
            patch("app.pipelines.tts_pipeline.model_manager"),
            patch("app.pipelines.tts_pipeline.synthesize_builtin", return_value=True),
            patch("app.pipelines.tts_pipeline.upload_to_s3", return_value="http://s3/tts/audio.wav"),
        ):
            result = pipeline.execute(JOB_ID, "Hello world", "Tammie", "wav", progress)

        assert isinstance(result, TtsJobResult)
        assert result.format == "wav"
        assert result.audio_url == "http://s3/tts/audio.wav"

    def test_returns_tts_job_result_mp3(self, pipeline, progress, tmp_path):
        with (
            patch.object(pipeline, "_make_tmp", return_value=str(tmp_path)),
            patch.object(pipeline, "_cleanup_tmp"),
            patch("app.pipelines.tts_pipeline.model_manager"),
            patch("app.pipelines.tts_pipeline.synthesize_builtin", return_value=True),
            patch("app.pipelines.tts_pipeline.subprocess.run") as mock_run,
            patch("app.pipelines.tts_pipeline.upload_to_s3", return_value="http://s3/tts/audio.mp3"),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            result = pipeline.execute(JOB_ID, "Hello world", "Tammie", "mp3", progress)

        assert result.format == "mp3"
        assert result.audio_url == "http://s3/tts/audio.mp3"

    def test_mp3_format_runs_ffmpeg_conversion(self, pipeline, progress, tmp_path):
        with (
            patch.object(pipeline, "_make_tmp", return_value=str(tmp_path)),
            patch.object(pipeline, "_cleanup_tmp"),
            patch("app.pipelines.tts_pipeline.model_manager"),
            patch("app.pipelines.tts_pipeline.synthesize_builtin", return_value=True),
            patch("app.pipelines.tts_pipeline.subprocess.run") as mock_run,
            patch("app.pipelines.tts_pipeline.upload_to_s3", return_value="http://s3/tts/audio.mp3"),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            pipeline.execute(JOB_ID, "Hello world", "Tammie", "mp3", progress)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "ffmpeg" in cmd
        assert "libmp3lame" in cmd

    def test_wav_format_skips_ffmpeg_conversion(self, pipeline, progress, tmp_path):
        with (
            patch.object(pipeline, "_make_tmp", return_value=str(tmp_path)),
            patch.object(pipeline, "_cleanup_tmp"),
            patch("app.pipelines.tts_pipeline.model_manager"),
            patch("app.pipelines.tts_pipeline.synthesize_builtin", return_value=True),
            patch("app.pipelines.tts_pipeline.subprocess.run") as mock_run,
            patch("app.pipelines.tts_pipeline.upload_to_s3", return_value="http://s3/tts/audio.wav"),
        ):
            pipeline.execute(JOB_ID, "Hello world", "Tammie", "wav", progress)

        mock_run.assert_not_called()

    def test_synthesis_failure_raises(self, pipeline, progress, tmp_path):
        with (
            patch.object(pipeline, "_make_tmp", return_value=str(tmp_path)),
            patch.object(pipeline, "_cleanup_tmp"),
            patch("app.pipelines.tts_pipeline.model_manager"),
            patch("app.pipelines.tts_pipeline.synthesize_builtin", return_value=False),
        ):
            with pytest.raises(RuntimeError, match="TTS synthesis failed"):
                pipeline.execute(JOB_ID, "Hello world", "Tammie", "wav", progress)

    def test_mp3_ffmpeg_failure_raises(self, pipeline, progress, tmp_path):
        with (
            patch.object(pipeline, "_make_tmp", return_value=str(tmp_path)),
            patch.object(pipeline, "_cleanup_tmp"),
            patch("app.pipelines.tts_pipeline.model_manager"),
            patch("app.pipelines.tts_pipeline.synthesize_builtin", return_value=True),
            patch(
                "app.pipelines.tts_pipeline.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "ffmpeg"),
            ),
        ):
            with pytest.raises(subprocess.CalledProcessError):
                pipeline.execute(JOB_ID, "Hello world", "Tammie", "mp3", progress)

    def test_releases_tts_model_after_synthesis(self, pipeline, progress, tmp_path):
        with (
            patch.object(pipeline, "_make_tmp", return_value=str(tmp_path)),
            patch.object(pipeline, "_cleanup_tmp"),
            patch("app.pipelines.tts_pipeline.model_manager") as mock_mm,
            patch("app.pipelines.tts_pipeline.synthesize_builtin", return_value=True),
            patch("app.pipelines.tts_pipeline.upload_to_s3", return_value="http://s3/tts/audio.wav"),
        ):
            pipeline.execute(JOB_ID, "Hello world", "Tammie", "wav", progress)

        mock_mm.release_tts.assert_called_once()

    def test_releases_whisper_before_synthesis(self, pipeline, progress, tmp_path):
        call_order = []

        with (
            patch.object(pipeline, "_make_tmp", return_value=str(tmp_path)),
            patch.object(pipeline, "_cleanup_tmp"),
            patch("app.pipelines.tts_pipeline.model_manager") as mock_mm,
            patch(
                "app.pipelines.tts_pipeline.synthesize_builtin",
                side_effect=lambda *a, **kw: call_order.append("synthesize") or True,
            ),
            patch("app.pipelines.tts_pipeline.upload_to_s3", return_value="http://s3/tts/audio.wav"),
        ):
            mock_mm.release_whisper.side_effect = lambda: call_order.append("release_whisper")
            pipeline.execute(JOB_ID, "Hello world", "Tammie", "wav", progress)

        assert call_order.index("release_whisper") < call_order.index("synthesize")

    def test_uploads_to_tts_s3_prefix(self, pipeline, progress, tmp_path):
        uploaded_keys = []

        with (
            patch.object(pipeline, "_make_tmp", return_value=str(tmp_path)),
            patch.object(pipeline, "_cleanup_tmp"),
            patch("app.pipelines.tts_pipeline.model_manager"),
            patch("app.pipelines.tts_pipeline.synthesize_builtin", return_value=True),
            patch(
                "app.pipelines.tts_pipeline.upload_to_s3",
                side_effect=lambda path, key: uploaded_keys.append(key) or f"http://s3/{key}",
            ),
        ):
            pipeline.execute(JOB_ID, "Hello world", "Tammie", "wav", progress)

        assert len(uploaded_keys) == 1
        assert uploaded_keys[0] == f"tts/{JOB_ID}.wav"
