import pytest
from io import BytesIO
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def _upload(client, project_id="my-project", filename="test.mp4", content=b"fake video"):
    return client.post(
        f"/videos/upload?project_id={project_id}",
        files={"file": (filename, BytesIO(content), "video/mp4")},
    )


class TestUploadVideo:
    def test_success_returns_200(self, client):
        with patch("app.routers.videos.storage") as mock_storage:
            mock_storage.upload_file.return_value = True
            mock_storage.get_base_url.return_value = "http://minio:9000/video-bucket"

            response = _upload(client)

        assert response.status_code == 200

    def test_success_response_body(self, client):
        with patch("app.routers.videos.storage") as mock_storage:
            mock_storage.upload_file.return_value = True
            mock_storage.get_base_url.return_value = "http://minio:9000/video-bucket"

            response = _upload(client, project_id="proj-abc")

        data = response.json()
        assert data["project_id"] == "proj-abc"
        assert data["message"] == "Video uploaded successfully"
        assert "proj-abc/video.mp4" in data["upload_url"]

    def test_success_object_name_uses_extension(self, client):
        with patch("app.routers.videos.storage") as mock_storage:
            mock_storage.upload_file.return_value = True
            mock_storage.get_base_url.return_value = "http://minio:9000/video-bucket"

            response = _upload(client, filename="clip.avi")

        assert "video.avi" in response.json()["upload_url"]

    def test_failure_message(self, client):
        with patch("app.routers.videos.storage") as mock_storage:
            mock_storage.upload_file.return_value = False
            mock_storage.get_base_url.return_value = "http://minio:9000/video-bucket"

            response = _upload(client)

        assert response.status_code == 200
        assert response.json()["message"] == "Failed to upload video"

    def test_upload_file_called_with_correct_object_name(self, client):
        with patch("app.routers.videos.storage") as mock_storage:
            mock_storage.upload_file.return_value = True
            mock_storage.get_base_url.return_value = "http://minio:9000/video-bucket"

            _upload(client, project_id="proj-xyz", filename="movie.mp4")

        call_args = mock_storage.upload_file.call_args
        object_name = call_args[0][1]
        assert object_name == "proj-xyz/video.mp4"
