from datetime import datetime
import pytest
from pydantic import ValidationError

from app.models.project import (
    ProjectCreationResponse,
    ProjectResponse,
    ProjectListResponse,
)
from app.models.video import VideoUploadResponse


class TestProjectCreationResponse:
    def test_valid(self):
        model = ProjectCreationResponse(
            project_id="abc123",
            message="Created",
            metadata={"title": "Test Video"},
        )
        assert model.project_id == "abc123"
        assert model.message == "Created"
        assert model.metadata["title"] == "Test Video"

    def test_missing_metadata_raises(self):
        with pytest.raises(ValidationError):
            ProjectCreationResponse(project_id="abc123", message="Created")

    def test_missing_project_id_raises(self):
        with pytest.raises(ValidationError):
            ProjectCreationResponse(message="Created", metadata={})


class TestProjectResponse:
    def test_valid(self):
        now = datetime.now()
        model = ProjectResponse(
            project_id="abc123",
            metadata={"title": "Test"},
            created_at=now,
            updated_at=now,
        )
        assert model.project_id == "abc123"
        assert model.created_at == now

    def test_invalid_datetime_raises(self):
        with pytest.raises(ValidationError):
            ProjectResponse(
                project_id="abc123",
                metadata={},
                created_at="not-a-date",
                updated_at="not-a-date",
            )

    def test_missing_created_at_raises(self):
        with pytest.raises(ValidationError):
            ProjectResponse(project_id="abc123", metadata={}, updated_at=datetime.now())


class TestProjectListResponse:
    def test_empty_list(self):
        model = ProjectListResponse(projects=[])
        assert model.projects == []

    def test_with_projects(self):
        now = datetime.now()
        model = ProjectListResponse(
            projects=[
                ProjectResponse(
                    project_id="1", metadata={}, created_at=now, updated_at=now
                )
            ]
        )
        assert len(model.projects) == 1
        assert model.projects[0].project_id == "1"

    def test_invalid_project_entry_raises(self):
        with pytest.raises(ValidationError):
            ProjectListResponse(projects=[{"project_id": "x"}])  # missing fields


class TestVideoUploadResponse:
    def test_valid(self):
        model = VideoUploadResponse(
            project_id="proj-1",
            message="Uploaded",
            upload_url="http://minio:9000/bucket/video.mp4",
        )
        assert model.project_id == "proj-1"
        assert model.upload_url == "http://minio:9000/bucket/video.mp4"

    def test_missing_upload_url_raises(self):
        with pytest.raises(ValidationError):
            VideoUploadResponse(project_id="proj-1", message="Uploaded")
