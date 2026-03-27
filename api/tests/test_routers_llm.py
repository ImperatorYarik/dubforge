import pytest
from unittest.mock import AsyncMock, MagicMock, patch


MOCK_VIDEO = {
    "video_id": "vid-1234",
    "project_id": "proj-1234",
    "video_url": "http://minio:9000/video-bucket/proj-1234/video.mp4",
    "transcript_segments": [{"start": 0.0, "end": 2.5, "text": "Hola mundo"}],
}


@pytest.fixture
def client():
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


class TestCollectContext:
    def test_success_returns_task_id_and_status(self, client):
        with (
            patch("app.routers.llm.videos_repo") as mock_videos,
            patch("app.routers.llm.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            mock_task = MagicMock()
            mock_task.id = "task-context-1"
            mock_celery.send_task.return_value = mock_task

            resp = client.post("/llm/collect-context?project_id=proj-1&video_id=vid-1")

        assert resp.status_code == 200
        assert resp.json()["task_id"] == "task-context-1"
        assert resp.json()["status"] == "submitted"

    def test_video_not_found_returns_error(self, client):
        with patch("app.routers.llm.videos_repo") as mock_videos:
            mock_videos.get_video = AsyncMock(return_value=None)
            resp = client.post("/llm/collect-context?project_id=proj-1&video_id=nonexistent")

        assert resp.status_code == 200
        assert "error" in resp.json()
        assert resp.json()["error"] == "Video not found"

    def test_no_segments_returns_error(self, client):
        video_no_segs = {**MOCK_VIDEO, "transcript_segments": []}
        with patch("app.routers.llm.videos_repo") as mock_videos:
            mock_videos.get_video = AsyncMock(return_value=video_no_segs)
            resp = client.post("/llm/collect-context?project_id=proj-1&video_id=vid-1")

        assert "error" in resp.json()

    def test_missing_segments_key_returns_error(self, client):
        video_no_segs = {k: v for k, v in MOCK_VIDEO.items() if k != "transcript_segments"}
        with patch("app.routers.llm.videos_repo") as mock_videos:
            mock_videos.get_video = AsyncMock(return_value=video_no_segs)
            resp = client.post("/llm/collect-context?project_id=proj-1&video_id=vid-1")

        assert "error" in resp.json()

    def test_calls_celery_with_segments(self, client):
        with (
            patch("app.routers.llm.videos_repo") as mock_videos,
            patch("app.routers.llm.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            mock_task = MagicMock()
            mock_task.id = "task-ctx"
            mock_celery.send_task.return_value = mock_task

            client.post("/llm/collect-context?project_id=proj-1&video_id=vid-1")

        call_kwargs = mock_celery.send_task.call_args[1]["kwargs"]
        assert call_kwargs["segments"] == MOCK_VIDEO["transcript_segments"]

    def test_model_param_forwarded(self, client):
        with (
            patch("app.routers.llm.videos_repo") as mock_videos,
            patch("app.routers.llm.celery") as mock_celery,
        ):
            mock_videos.get_video = AsyncMock(return_value=MOCK_VIDEO)
            mock_task = MagicMock()
            mock_task.id = "task-ctx"
            mock_celery.send_task.return_value = mock_task

            client.post("/llm/collect-context?project_id=proj-1&video_id=vid-1&model=mistral")

        call_kwargs = mock_celery.send_task.call_args[1]["kwargs"]
        assert call_kwargs["model"] == "mistral"


class TestGetContextStatus:
    def test_success_returns_context(self, client):
        mock_result = MagicMock()
        mock_result.state = "SUCCESS"
        mock_result.result = {"context": "Spanish cooking show", "model": "llama3.2"}

        with patch("app.routers.llm.AsyncResult", return_value=mock_result):
            resp = client.get("/llm/task-ctx-1/context-status")

        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"
        assert resp.json()["context"] == "Spanish cooking show"
        assert resp.json()["model"] == "llama3.2"

    def test_failure_returns_error(self, client):
        mock_result = MagicMock()
        mock_result.state = "FAILURE"
        mock_result.result = Exception("Something went wrong")

        with patch("app.routers.llm.AsyncResult", return_value=mock_result):
            resp = client.get("/llm/task-ctx-fail/context-status")

        assert resp.json()["status"] == "failed"
        assert "error" in resp.json()

    def test_pending_returns_pending_status(self, client):
        mock_result = MagicMock()
        mock_result.state = "PENDING"

        with patch("app.routers.llm.AsyncResult", return_value=mock_result):
            resp = client.get("/llm/task-ctx-pend/context-status")

        assert resp.json()["status"] == "pending"


class TestTranslateSegments:
    def test_success_returns_task_id(self, client):
        with patch("app.routers.llm.celery") as mock_celery:
            mock_task = MagicMock()
            mock_task.id = "task-translate-1"
            mock_celery.send_task.return_value = mock_task

            resp = client.post("/llm/translate-segments", json={
                "video_id": "vid-1",
                "segments": [{"start": 0.0, "end": 2.5, "text": "Hola mundo"}],
                "context": "Spanish greeting",
                "model": "llama3.2",
            })

        assert resp.status_code == 200
        assert resp.json()["task_id"] == "task-translate-1"
        assert resp.json()["status"] == "submitted"

    def test_calls_celery_with_correct_args(self, client):
        with patch("app.routers.llm.celery") as mock_celery:
            mock_task = MagicMock()
            mock_task.id = "task-tr"
            mock_celery.send_task.return_value = mock_task

            client.post("/llm/translate-segments", json={
                "video_id": "vid-1",
                "segments": [{"start": 0.0, "end": 2.5, "text": "Hola"}],
                "context": "test context",
                "model": "llama3.2",
            })

        call_kwargs = mock_celery.send_task.call_args[1]["kwargs"]
        assert call_kwargs["context"] == "test context"
        assert call_kwargs["segments"][0]["text"] == "Hola"
        assert call_kwargs["model"] == "llama3.2"


class TestGetTranslateStatus:
    def test_success_returns_segments(self, client):
        mock_result = MagicMock()
        mock_result.state = "SUCCESS"
        mock_result.result = {"segments": [{"start": 0.0, "end": 2.5, "text": "Hello world"}]}

        with patch("app.routers.llm.AsyncResult", return_value=mock_result):
            resp = client.get("/llm/task-tr-1/translate-status")

        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"
        assert resp.json()["segments"][0]["text"] == "Hello world"

    def test_pending_returns_pending_status(self, client):
        mock_result = MagicMock()
        mock_result.state = "PENDING"

        with patch("app.routers.llm.AsyncResult", return_value=mock_result):
            resp = client.get("/llm/task-tr-pend/translate-status")

        assert resp.json()["status"] == "pending"


class TestGetModels:
    def test_returns_model_list_on_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "llama3.2"}, {"name": "mistral"}]
        }
        mock_async_client = AsyncMock()
        mock_async_client.get = AsyncMock(return_value=mock_response)

        with patch("app.routers.llm.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            resp = client.get("/llm/models")

        assert resp.status_code == 200
        assert "llama3.2" in resp.json()["models"]
        assert "mistral" in resp.json()["models"]

    def test_returns_empty_list_when_ollama_unreachable(self, client):
        mock_async_client = AsyncMock()
        mock_async_client.get = AsyncMock(side_effect=Exception("Connection refused"))

        with patch("app.routers.llm.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            resp = client.get("/llm/models")

        assert resp.status_code == 200
        assert resp.json()["models"] == []

    def test_returns_empty_list_on_non_200(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_async_client = AsyncMock()
        mock_async_client.get = AsyncMock(return_value=mock_response)

        with patch("app.routers.llm.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            resp = client.get("/llm/models")

        assert resp.status_code == 200
        assert resp.json()["models"] == []
