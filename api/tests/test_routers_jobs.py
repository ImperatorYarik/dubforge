import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call


MOCK_VIDEO = {
    "video_id": "vid-1234",
    "project_id": "proj-1234",
    "video_url": "http://minio:9000/video-bucket/proj-1234/video.mp4",
    "transcription": "[0.00s - 2.50s] Hello world\n",
    "transcript_segments": [{"start": 0.0, "end": 2.5, "text": "Hello world"}],
    "transcript_url": None,
    "dubbed_url": None,
    "vocals_url": None,
    "no_vocals_url": None,
    "detected_language": "es",
    "duration_seconds": 120.5,
    "created_at": datetime(2026, 1, 1),
    "updated_at": datetime(2026, 1, 1),
}


@pytest.fixture
def client():
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_register_job():
    """Prevent register_job from connecting to Redis in all router tests."""
    with patch("app.routers.jobs.register_job", new=AsyncMock()):
        yield


@pytest.fixture(autouse=True)
def mock_storage_exists():
    """Default storage pre-flight to True so existing tests are unaffected."""
    with patch("app.routers.jobs.storage") as mock_storage:
        mock_storage.object_exists.return_value = True
        yield mock_storage


class TestDubVideo:
    def test_returns_task_id(self, client):
        with (
            patch("app.routers.jobs.videos_repo") as mock_videos,
            patch("app.routers.jobs.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            mock_task = MagicMock()
            mock_task.id = "task-abc"
            mock_celery.send_task.return_value = mock_task

            resp = client.post("/jobs/dub?project_id=proj-1&video_id=vid-1")

        assert resp.status_code == 200
        assert resp.json()["task_id"] == "task-abc"
        assert resp.json()["status"] == "submitted"

    def test_skip_transcription_param_passed(self, client):
        with (
            patch("app.routers.jobs.videos_repo") as mock_videos,
            patch("app.routers.jobs.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            mock_task = MagicMock()
            mock_task.id = "task-xyz"
            mock_celery.send_task.return_value = mock_task

            client.post("/jobs/dub?project_id=proj-1&video_id=vid-1&skip_transcription=true")

        call_kwargs = mock_celery.send_task.call_args[1]["kwargs"]
        assert call_kwargs["skip_transcription"] is True

    def test_vocals_url_passed_to_task(self, client):
        video_with_vocals = {
            **MOCK_VIDEO,
            "vocals_url": "http://s3/vocals.wav",
            "no_vocals_url": "http://s3/no_vocals.wav",
        }
        with (
            patch("app.routers.jobs.videos_repo") as mock_videos,
            patch("app.routers.jobs.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=video_with_vocals)
            mock_task = MagicMock()
            mock_task.id = "task-vocals"
            mock_celery.send_task.return_value = mock_task

            client.post("/jobs/dub?project_id=proj-1&video_id=vid-1")

        call_kwargs = mock_celery.send_task.call_args[1]["kwargs"]
        assert call_kwargs["vocals_url"] == "http://s3/vocals.wav"
        assert call_kwargs["no_vocals_url"] == "http://s3/no_vocals.wav"

    def test_skip_transcription_passes_existing_data(self, client):
        with (
            patch("app.routers.jobs.videos_repo") as mock_videos,
            patch("app.routers.jobs.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            mock_task = MagicMock()
            mock_task.id = "task-skip"
            mock_celery.send_task.return_value = mock_task

            client.post("/jobs/dub?project_id=proj-1&video_id=vid-1&skip_transcription=true")

        call_kwargs = mock_celery.send_task.call_args[1]["kwargs"]
        assert call_kwargs["existing_transcription"] == MOCK_VIDEO["transcription"]
        assert call_kwargs["existing_segments"] == MOCK_VIDEO["transcript_segments"]
        assert call_kwargs["existing_detected_language"] == MOCK_VIDEO["detected_language"]
        assert call_kwargs["existing_duration_seconds"] == MOCK_VIDEO["duration_seconds"]

    def test_no_transcription_when_skip_false(self, client):
        with (
            patch("app.routers.jobs.videos_repo") as mock_videos,
            patch("app.routers.jobs.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            mock_task = MagicMock()
            mock_task.id = "task-noskip"
            mock_celery.send_task.return_value = mock_task

            client.post("/jobs/dub?project_id=proj-1&video_id=vid-1&skip_transcription=false")

        call_kwargs = mock_celery.send_task.call_args[1]["kwargs"]
        assert call_kwargs["existing_transcription"] is None
        assert call_kwargs["existing_segments"] is None

    def test_ducking_params_passed(self, client):
        with (
            patch("app.routers.jobs.videos_repo") as mock_videos,
            patch("app.routers.jobs.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            mock_task = MagicMock()
            mock_task.id = "task-duck"
            mock_celery.send_task.return_value = mock_task

            client.post(
                "/jobs/dub?project_id=proj-1&video_id=vid-1"
                "&ducking_enabled=false&ducking_level=0.5"
            )

        call_kwargs = mock_celery.send_task.call_args[1]["kwargs"]
        assert call_kwargs["ducking_enabled"] is False
        assert call_kwargs["ducking_level"] == 0.5

    def test_atempo_params_clamped(self, client):
        with (
            patch("app.routers.jobs.videos_repo") as mock_videos,
            patch("app.routers.jobs.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            mock_task = MagicMock()
            mock_task.id = "task-atempo"
            mock_celery.send_task.return_value = mock_task

            # Values outside range should be clamped
            client.post(
                "/jobs/dub?project_id=proj-1&video_id=vid-1"
                "&atempo_min=0.1&atempo_max=5.0"
            )

        call_kwargs = mock_celery.send_task.call_args[1]["kwargs"]
        assert call_kwargs["atempo_min"] == 0.5   # clamped from 0.1
        assert call_kwargs["atempo_max"] == 2.0   # clamped from 5.0

    def test_atempo_params_in_range(self, client):
        with (
            patch("app.routers.jobs.videos_repo") as mock_videos,
            patch("app.routers.jobs.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            mock_task = MagicMock()
            mock_task.id = "task-atempo2"
            mock_celery.send_task.return_value = mock_task

            client.post(
                "/jobs/dub?project_id=proj-1&video_id=vid-1"
                "&atempo_min=0.8&atempo_max=1.4"
            )

        call_kwargs = mock_celery.send_task.call_args[1]["kwargs"]
        assert call_kwargs["atempo_min"] == 0.8
        assert call_kwargs["atempo_max"] == 1.4

    def test_video_not_found(self, client):
        with patch("app.routers.jobs.videos_repo") as mock_videos:
            mock_videos.get_video = AsyncMock(return_value=None)
            resp = client.post("/jobs/dub?project_id=proj-1&video_id=nonexistent")

        assert resp.json()["error"] == "Video not found"

    def test_returns_error_when_source_file_missing_from_storage(self, client, mock_storage_exists):
        mock_storage_exists.object_exists.return_value = False
        with patch("app.routers.jobs.videos_repo") as mock_videos:
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            resp = client.post("/jobs/dub?project_id=proj-1&video_id=vid-1")

        assert "error" in resp.json()

    def test_does_not_enqueue_when_source_file_missing(self, client, mock_storage_exists):
        mock_storage_exists.object_exists.return_value = False
        with (
            patch("app.routers.jobs.videos_repo") as mock_videos,
            patch("app.routers.jobs.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            client.post("/jobs/dub?project_id=proj-1&video_id=vid-1")

        mock_celery.send_task.assert_not_called()


class TestTranscribeVideo:
    def test_returns_task_id(self, client):
        with (
            patch("app.routers.jobs.videos_repo") as mock_videos,
            patch("app.routers.jobs.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            mock_task = MagicMock()
            mock_task.id = "task-tr"
            mock_celery.send_task.return_value = mock_task

            resp = client.post("/jobs/transcribe?project_id=proj-1&video_id=vid-1")

        assert resp.status_code == 200
        assert resp.json()["task_id"] == "task-tr"

    def test_model_param_passed(self, client):
        with (
            patch("app.routers.jobs.videos_repo") as mock_videos,
            patch("app.routers.jobs.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            mock_task = MagicMock()
            mock_task.id = "task-model"
            mock_celery.send_task.return_value = mock_task

            client.post("/jobs/transcribe?project_id=proj-1&video_id=vid-1&model=medium")

        call_kwargs = mock_celery.send_task.call_args[1]["kwargs"]
        assert call_kwargs["model"] == "medium"

    def test_invalid_model_rejected(self, client):
        with patch("app.routers.jobs.videos_repo") as mock_videos:
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            resp = client.post("/jobs/transcribe?project_id=proj-1&video_id=vid-1&model=invalid-model")

        assert "error" in resp.json()
        assert "invalid" in resp.json()["error"].lower()

    def test_valid_models_accepted(self, client):
        valid_models = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
        for m in valid_models:
            with (
                patch("app.routers.jobs.videos_repo") as mock_videos,
                patch("app.routers.jobs.celery") as mock_celery,
            ):
                mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
                mock_task = MagicMock()
                mock_task.id = f"task-{m}"
                mock_celery.send_task.return_value = mock_task

                resp = client.post(f"/jobs/transcribe?project_id=proj-1&video_id=vid-1&model={m}")

            assert "error" not in resp.json(), f"Model {m} should be valid"

    def test_skip_demucs_param_passed(self, client):
        with (
            patch("app.routers.jobs.videos_repo") as mock_videos,
            patch("app.routers.jobs.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            mock_task = MagicMock()
            mock_task.id = "task-skip-demucs"
            mock_celery.send_task.return_value = mock_task

            client.post("/jobs/transcribe?project_id=proj-1&video_id=vid-1&skip_demucs=true")

        call_kwargs = mock_celery.send_task.call_args[1]["kwargs"]
        assert call_kwargs["skip_demucs"] is True

    def test_language_param_passed(self, client):
        with (
            patch("app.routers.jobs.videos_repo") as mock_videos,
            patch("app.routers.jobs.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            mock_task = MagicMock()
            mock_task.id = "task-lang"
            mock_celery.send_task.return_value = mock_task

            client.post("/jobs/transcribe?project_id=proj-1&video_id=vid-1&language=es")

        call_kwargs = mock_celery.send_task.call_args[1]["kwargs"]
        assert call_kwargs["language"] == "es"

    def test_translate_param_passed(self, client):
        with (
            patch("app.routers.jobs.videos_repo") as mock_videos,
            patch("app.routers.jobs.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            mock_task = MagicMock()
            mock_task.id = "task-notranslate"
            mock_celery.send_task.return_value = mock_task

            client.post("/jobs/transcribe?project_id=proj-1&video_id=vid-1&translate=false")

        call_kwargs = mock_celery.send_task.call_args[1]["kwargs"]
        assert call_kwargs["translate"] is False

    def test_vocals_url_passed_to_task(self, client):
        video_with_vocals = {
            **MOCK_VIDEO,
            "vocals_url": "http://s3/vocals.wav",
            "no_vocals_url": "http://s3/no_vocals.wav",
        }
        with (
            patch("app.routers.jobs.videos_repo") as mock_videos,
            patch("app.routers.jobs.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=video_with_vocals)
            mock_task = MagicMock()
            mock_task.id = "task-tr-vocals"
            mock_celery.send_task.return_value = mock_task

            client.post("/jobs/transcribe?project_id=proj-1&video_id=vid-1")

        call_kwargs = mock_celery.send_task.call_args[1]["kwargs"]
        assert call_kwargs["vocals_url"] == "http://s3/vocals.wav"
        assert call_kwargs["no_vocals_url"] == "http://s3/no_vocals.wav"

    def test_returns_error_when_source_file_missing_from_storage(self, client, mock_storage_exists):
        mock_storage_exists.object_exists.return_value = False
        with patch("app.routers.jobs.videos_repo") as mock_videos:
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            resp = client.post("/jobs/transcribe?project_id=proj-1&video_id=vid-1")

        assert "error" in resp.json()

    def test_does_not_enqueue_when_source_file_missing(self, client, mock_storage_exists):
        mock_storage_exists.object_exists.return_value = False
        with (
            patch("app.routers.jobs.videos_repo") as mock_videos,
            patch("app.routers.jobs.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            client.post("/jobs/transcribe?project_id=proj-1&video_id=vid-1")

        mock_celery.send_task.assert_not_called()


class TestGetJobStatus:
    def test_success_returns_enriched_shape(self, client):
        mock_result = MagicMock()
        mock_result.state = "SUCCESS"
        mock_result.result = {
            "status": "completed",
            "dubbed_url": "http://minio:9000/video-bucket/proj-1/dubbed.mp4",
            "video_id": "vid-1234",
            "job_id": "job-1",
        }

        with (
            patch("app.routers.jobs.AsyncResult", return_value=mock_result),
            patch("app.routers.jobs.persist_job_result", new=AsyncMock()),
            patch("app.services.jobs.storage") as mock_storage,
        ):
            mock_storage.generate_presigned_url.return_value = (
                "http://minio:9000/video-bucket/proj-1/dubbed.mp4?sig=abc"
            )

            resp = client.get("/jobs/task-123/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-123"
        assert data["state"] == "SUCCESS"
        assert data["status"] == "completed"
        assert data["pct"] == 100
        assert "result" in data

    def test_success_calls_persist_job_result(self, client):
        mock_result = MagicMock()
        mock_result.state = "SUCCESS"
        mock_result.result = {
            "status": "completed",
            "dubbed_url": "http://s3/dubbed.mp4",
            "video_id": "vid-1234",
            "job_id": "job-1",
        }

        with (
            patch("app.routers.jobs.AsyncResult", return_value=mock_result),
            patch("app.routers.jobs.persist_job_result", new=AsyncMock()) as mock_persist,
            patch("app.services.jobs.storage") as mock_storage,
        ):
            mock_storage.generate_presigned_url.return_value = "http://s3/dubbed.mp4?sig=x"
            client.get("/jobs/task-persist/status")

        mock_persist.assert_called_once_with(mock_result.result)

    def test_failure_returns_error_field(self, client):
        mock_result = MagicMock()
        mock_result.state = "FAILURE"
        mock_result.result = Exception("Something went wrong")

        with patch("app.routers.jobs.AsyncResult", return_value=mock_result):
            resp = client.get("/jobs/task-fail/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "FAILURE"
        assert data["status"] == "failed"
        assert "error" in data

    def test_pending_returns_pending_state(self, client):
        mock_result = MagicMock()
        mock_result.state = "PENDING"

        with patch("app.routers.jobs.AsyncResult", return_value=mock_result):
            resp = client.get("/jobs/task-pending/status")

        assert resp.status_code == 200
        assert resp.json()["state"] == "PENDING"
        assert resp.json()["status"] == "pending"

    def test_status_response_has_required_fields(self, client):
        mock_result = MagicMock()
        mock_result.state = "STARTED"

        with patch("app.routers.jobs.AsyncResult", return_value=mock_result):
            resp = client.get("/jobs/task-started/status")

        data = resp.json()
        for field in ["task_id", "state", "status", "pct", "step", "message"]:
            assert field in data, f"Missing field: {field}"
