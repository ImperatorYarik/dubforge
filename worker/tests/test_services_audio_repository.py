import pytest
from unittest.mock import MagicMock, patch
from app.models.audio import SeparationResult
from app.services.audio_repository import AudioRepository


@pytest.fixture
def repo():
    return AudioRepository()


class TestDownloadCachedSeparation:
    def test_returns_none_when_no_video_doc(self, repo):
        with patch("app.services.audio_repository.videos_collection") as mock_col:
            mock_col.find_one.return_value = None
            result = repo.download_cached_separation("vid1", "/tmp/test")
        assert result is None

    def test_returns_none_when_no_vocals_url(self, repo):
        with patch("app.services.audio_repository.videos_collection") as mock_col:
            mock_col.find_one.return_value = {"video_id": "vid1"}
            result = repo.download_cached_separation("vid1", "/tmp/test")
        assert result is None

    def test_returns_separation_result_on_cache_hit(self, repo):
        video_doc = {
            "video_id": "vid1",
            "vocals_url": "http://s3/vocals.wav",
            "no_vocals_url": "http://s3/no_vocals.wav",
        }
        with (
            patch("app.services.audio_repository.videos_collection") as mock_col,
            patch("app.services.audio_repository.download_file_to_disk", return_value=True),
        ):
            mock_col.find_one.return_value = video_doc
            result = repo.download_cached_separation("vid1", "/tmp/test")

        assert isinstance(result, SeparationResult)
        assert result.vocals_path == "/tmp/test/vocals.wav"
        assert result.no_vocals_path == "/tmp/test/no_vocals.wav"

    def test_raises_when_vocals_download_fails(self, repo):
        video_doc = {"video_id": "vid1", "vocals_url": "http://s3/vocals.wav"}
        with (
            patch("app.services.audio_repository.videos_collection") as mock_col,
            patch("app.services.audio_repository.download_file_to_disk", return_value=False),
        ):
            mock_col.find_one.return_value = video_doc
            with pytest.raises(RuntimeError, match="Failed to download existing vocals"):
                repo.download_cached_separation("vid1", "/tmp/test")

    def test_downloads_no_vocals_when_url_present(self, repo):
        video_doc = {
            "video_id": "vid1",
            "vocals_url": "http://s3/vocals.wav",
            "no_vocals_url": "http://s3/no_vocals.wav",
        }
        with (
            patch("app.services.audio_repository.videos_collection") as mock_col,
            patch("app.services.audio_repository.download_file_to_disk", return_value=True) as mock_dl,
        ):
            mock_col.find_one.return_value = video_doc
            repo.download_cached_separation("vid1", "/tmp/test")

        assert mock_dl.call_count == 2

    def test_skips_no_vocals_download_when_url_absent(self, repo):
        video_doc = {"video_id": "vid1", "vocals_url": "http://s3/vocals.wav"}
        with (
            patch("app.services.audio_repository.videos_collection") as mock_col,
            patch("app.services.audio_repository.download_file_to_disk", return_value=True) as mock_dl,
        ):
            mock_col.find_one.return_value = video_doc
            repo.download_cached_separation("vid1", "/tmp/test")

        assert mock_dl.call_count == 1


class TestSaveSeparation:
    def test_uploads_vocals_and_no_vocals(self, repo):
        separation = SeparationResult(
            vocals_path="/tmp/vocals.wav",
            no_vocals_path="/tmp/no_vocals.wav",
        )
        with (
            patch("app.services.audio_repository.videos_collection") as mock_col,
            patch("app.services.audio_repository.upload_to_s3", return_value="http://s3/file") as mock_upload,
        ):
            repo.save_separation("vid1", "proj1", "job1", separation)

        assert mock_upload.call_count == 2

    def test_uploads_with_correct_s3_keys(self, repo):
        separation = SeparationResult(
            vocals_path="/tmp/vocals.wav",
            no_vocals_path="/tmp/no_vocals.wav",
        )
        uploaded_keys = []
        with (
            patch("app.services.audio_repository.videos_collection"),
            patch(
                "app.services.audio_repository.upload_to_s3",
                side_effect=lambda path, key: uploaded_keys.append(key) or "http://s3/file",
            ),
        ):
            repo.save_separation("vid1", "proj1", "job1", separation)

        assert "proj1/vocals_job1.wav" in uploaded_keys
        assert "proj1/no_vocals_job1.wav" in uploaded_keys

    def test_updates_mongodb_with_urls(self, repo):
        separation = SeparationResult(
            vocals_path="/tmp/vocals.wav",
            no_vocals_path="/tmp/no_vocals.wav",
        )
        with (
            patch("app.services.audio_repository.videos_collection") as mock_col,
            patch("app.services.audio_repository.upload_to_s3", return_value="http://s3/file"),
        ):
            repo.save_separation("vid1", "proj1", "job1", separation)

        mock_col.update_one.assert_called_once()
        filter_arg = mock_col.update_one.call_args[0][0]
        assert filter_arg == {"video_id": "vid1"}

    def test_returns_tuple_of_urls(self, repo):
        separation = SeparationResult(
            vocals_path="/tmp/vocals.wav",
            no_vocals_path="/tmp/no_vocals.wav",
        )
        with (
            patch("app.services.audio_repository.videos_collection"),
            patch(
                "app.services.audio_repository.upload_to_s3",
                side_effect=["http://s3/vocals.wav", "http://s3/no_vocals.wav"],
            ),
        ):
            vocals_url, no_vocals_url = repo.save_separation("vid1", "proj1", "job1", separation)

        assert vocals_url == "http://s3/vocals.wav"
        assert no_vocals_url == "http://s3/no_vocals.wav"
