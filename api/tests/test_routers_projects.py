import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


MOCK_METADATA = {
    "title": "Test Video",
    "description": "Desc",
    "thumbnail": "http://thumb.url/img.jpg",
    "duration": 100,
    "upload_date": "20260308",
    "uploader": "Channel",
}

MOCK_PROJECT = {
    "project_id": "test-uuid-1234",
    "metadata": MOCK_METADATA,
    "created_at": datetime(2026, 3, 8, 10, 0, 0),
    "updated_at": datetime(2026, 3, 8, 10, 0, 0),
}


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


class TestCreateProject:
    def test_success(self, client):
        with (
            patch("app.routers.projects.get_youtube_metadata", new=AsyncMock(return_value=MOCK_METADATA)),
            patch("app.routers.projects.projects") as mock_crud,
            patch("app.routers.projects.storage") as mock_storage,
        ):
            mock_crud.create_project = AsyncMock(return_value="test-uuid-1234")
            mock_storage.create_folder.return_value = True

            response = client.post(
                "/projects/create?youtube_url=https://youtube.com/watch?v=test"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == "test-uuid-1234"
        assert data["message"] == "Project created successfully"
        assert data["metadata"] == MOCK_METADATA

    def test_creates_folder_for_project(self, client):
        with (
            patch("app.routers.projects.get_youtube_metadata", new=AsyncMock(return_value=MOCK_METADATA)),
            patch("app.routers.projects.projects") as mock_crud,
            patch("app.routers.projects.storage") as mock_storage,
        ):
            mock_crud.create_project = AsyncMock(return_value="test-uuid-1234")
            mock_storage.create_folder.return_value = True

            client.post("/projects/create?youtube_url=https://youtube.com/watch?v=test")

        mock_storage.create_folder.assert_called_once_with("test-uuid-1234")


class TestListProjects:
    def test_empty_list(self, client):
        with patch("app.routers.projects.projects") as mock_crud:
            mock_crud.list_projects = AsyncMock(return_value=[])

            response = client.get("/projects/list_projects")

        assert response.status_code == 200
        assert response.json()["projects"] == []

    def test_returns_all_projects(self, client):
        with patch("app.routers.projects.projects") as mock_crud:
            mock_crud.list_projects = AsyncMock(return_value=[MOCK_PROJECT, MOCK_PROJECT])

            response = client.get("/projects/list_projects")

        assert response.status_code == 200
        assert len(response.json()["projects"]) == 2

    def test_project_fields_present(self, client):
        with patch("app.routers.projects.projects") as mock_crud:
            mock_crud.list_projects = AsyncMock(return_value=[MOCK_PROJECT])

            response = client.get("/projects/list_projects")

        project = response.json()["projects"][0]
        assert "project_id" in project
        assert "metadata" in project
        assert "created_at" in project
        assert "updated_at" in project


class TestGetProject:
    def test_found(self, client):
        with patch("app.routers.projects.projects") as mock_crud:
            mock_crud.get_project = AsyncMock(return_value=MOCK_PROJECT)

            response = client.get("/projects/test-uuid-1234")

        assert response.status_code == 200
        assert response.json()["project_id"] == "test-uuid-1234"
        assert response.json()["metadata"] == MOCK_METADATA

    def test_not_found(self, client):
        with patch("app.routers.projects.projects") as mock_crud:
            mock_crud.get_project = AsyncMock(return_value=None)

            response = client.get("/projects/nonexistent-id")

        assert response.status_code == 200
        assert response.json()["message"] == "Project not found"
