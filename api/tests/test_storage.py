import pytest
from io import BytesIO
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_s3():
    with patch("app.utils.storage.client") as mock_client:
        yield mock_client


@pytest.fixture
def mock_cfg():
    with patch("app.utils.storage.settings") as s:
        s.BUCKET_NAME = "test-bucket"
        s.S3_ENDPOINT = "http://localhost:9000"
        yield s


class TestCreateBucket:
    def test_success(self, mock_s3):
        mock_s3.create_bucket.return_value = {}
        from app.utils.storage import storage

        assert storage.create_bucket("test-bucket") is True
        mock_s3.create_bucket.assert_called_once_with(Bucket="test-bucket")

    def test_failure_returns_false(self, mock_s3):
        mock_s3.create_bucket.side_effect = Exception("Connection refused")
        from app.utils.storage import storage

        assert storage.create_bucket("test-bucket") is False


class TestCreateFolder:
    def test_success(self, mock_s3, mock_cfg):
        mock_s3.put_object.return_value = {}
        from app.utils.storage import storage

        assert storage.create_folder("my-folder") is True
        mock_s3.put_object.assert_called_once_with(
            Bucket="test-bucket", Key="my-folder/"
        )

    def test_trailing_slash_appended(self, mock_s3, mock_cfg):
        mock_s3.put_object.return_value = {}
        from app.utils.storage import storage

        storage.create_folder("videos")
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["Key"].endswith("/")

    def test_failure_returns_false(self, mock_s3, mock_cfg):
        mock_s3.put_object.side_effect = Exception("Bucket not found")
        from app.utils.storage import storage

        assert storage.create_folder("my-folder") is False


class TestUploadFile:
    def test_success(self, mock_s3, mock_cfg):
        mock_s3.upload_fileobj.return_value = {}
        from app.utils.storage import storage

        mock_file = MagicMock()
        mock_file.file = BytesIO(b"video content")

        assert storage.upload_file(mock_file, "folder/video.mp4") is True
        mock_s3.upload_fileobj.assert_called_once_with(
            mock_file.file, "test-bucket", "folder/video.mp4"
        )

    def test_failure_returns_false(self, mock_s3, mock_cfg):
        mock_s3.upload_fileobj.side_effect = Exception("Upload error")
        from app.utils.storage import storage

        mock_file = MagicMock()
        mock_file.file = BytesIO(b"data")

        assert storage.upload_file(mock_file, "folder/video.mp4") is False


class TestGetBaseUrl:
    def test_returns_endpoint_plus_bucket(self, mock_cfg):
        from app.utils.storage import storage

        url = storage.get_base_url()
        assert url == "http://localhost:9000/test-bucket"
