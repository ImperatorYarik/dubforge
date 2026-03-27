import pytest
from unittest.mock import patch, MagicMock
from app.models.segment import TranscriptSegment
from app.services.transcript_repository import TranscriptRepository


@pytest.fixture
def repo():
    return TranscriptRepository()


MOCK_SEGMENTS = [
    TranscriptSegment(start=0.0, end=5.0, text="Hello world"),
    TranscriptSegment(start=5.5, end=10.0, text="How are you"),
]


class TestGetExisting:
    def test_returns_none_when_no_video_doc(self, repo):
        with patch("app.services.transcript_repository.videos_collection") as mock_col:
            mock_col.find_one.return_value = None
            result = repo.get_existing("vid1")
        assert result is None

    def test_returns_none_when_no_transcription_text(self, repo):
        with patch("app.services.transcript_repository.videos_collection") as mock_col:
            mock_col.find_one.return_value = {"video_id": "vid1"}
            result = repo.get_existing("vid1")
        assert result is None

    def test_parses_plain_text_format(self, repo):
        text = "[0.00s - 5.00s] Hello world\n[5.50s - 10.00s] How are you\n"
        with patch("app.services.transcript_repository.videos_collection") as mock_col:
            mock_col.find_one.return_value = {"video_id": "vid1", "transcription": text}
            result = repo.get_existing("vid1")

        assert result is not None
        segments, returned_text = result
        assert len(segments) == 2
        assert segments[0].start == 0.0
        assert segments[0].end == 5.0
        assert segments[0].text == "Hello world"
        assert segments[1].start == 5.5
        assert segments[1].text == "How are you"

    def test_prefers_structured_segments_over_plain_text(self, repo):
        raw_segs = [
            {"start": 0.0, "end": 5.0, "text": "Structured segment"},
        ]
        text = "[0.00s - 5.00s] Plain text\n"
        with patch("app.services.transcript_repository.videos_collection") as mock_col:
            mock_col.find_one.return_value = {
                "video_id": "vid1",
                "transcription": text,
                "transcript_segments": raw_segs,
            }
            result = repo.get_existing("vid1")

        segments, _ = result
        assert segments[0].text == "Structured segment"

    def test_returns_none_when_plain_text_has_no_parseable_segments(self, repo):
        with patch("app.services.transcript_repository.videos_collection") as mock_col:
            mock_col.find_one.return_value = {
                "video_id": "vid1",
                "transcription": "No timestamps here",
            }
            result = repo.get_existing("vid1")
        assert result is None

    def test_returns_transcription_text_alongside_segments(self, repo):
        text = "[0.00s - 5.00s] Hello world\n"
        with patch("app.services.transcript_repository.videos_collection") as mock_col:
            mock_col.find_one.return_value = {"video_id": "vid1", "transcription": text}
            result = repo.get_existing("vid1")

        _, returned_text = result
        assert returned_text == text


class TestSaveTranscription:
    def test_writes_transcript_file(self, repo, tmp_path):
        with (
            patch("app.services.transcript_repository.videos_collection"),
            patch("app.services.transcript_repository.upload_to_s3", return_value="http://s3/t.txt"),
        ):
            repo.save_transcription("vid1", "proj1", "job1", MOCK_SEGMENTS, str(tmp_path))

        transcript_file = tmp_path / "transcription.txt"
        assert transcript_file.exists()
        content = transcript_file.read_text()
        assert "[0.00s - 5.00s] Hello world" in content
        assert "[5.50s - 10.00s] How are you" in content

    def test_uploads_to_correct_s3_key(self, repo, tmp_path):
        with (
            patch("app.services.transcript_repository.videos_collection"),
            patch("app.services.transcript_repository.upload_to_s3", return_value="http://s3/t.txt") as mock_upload,
        ):
            repo.save_transcription("vid1", "proj1", "job1", MOCK_SEGMENTS, str(tmp_path))

        mock_upload.assert_called_once()
        _, s3_key = mock_upload.call_args[0]
        assert s3_key == "proj1/transcription_job1.txt"

    def test_returns_transcript_url(self, repo, tmp_path):
        with (
            patch("app.services.transcript_repository.videos_collection"),
            patch("app.services.transcript_repository.upload_to_s3", return_value="http://s3/transcript.txt"),
        ):
            url = repo.save_transcription("vid1", "proj1", "job1", MOCK_SEGMENTS, str(tmp_path))

        assert url == "http://s3/transcript.txt"

    def test_updates_mongodb_with_transcription_fields(self, repo, tmp_path):
        with (
            patch("app.services.transcript_repository.videos_collection") as mock_col,
            patch("app.services.transcript_repository.upload_to_s3", return_value="http://s3/t.txt"),
        ):
            repo.save_transcription("vid1", "proj1", "job1", MOCK_SEGMENTS, str(tmp_path))

        mock_col.update_one.assert_called_once()
        filter_arg, update_arg = mock_col.update_one.call_args[0]
        assert filter_arg == {"video_id": "vid1"}
        set_fields = update_arg["$set"]
        assert "transcription" in set_fields
        assert "transcript_url" in set_fields
        assert "transcript_segments" in set_fields

    def test_stores_detected_language_when_provided(self, repo, tmp_path):
        with (
            patch("app.services.transcript_repository.videos_collection") as mock_col,
            patch("app.services.transcript_repository.upload_to_s3", return_value="http://s3/t.txt"),
        ):
            repo.save_transcription(
                "vid1", "proj1", "job1", MOCK_SEGMENTS, str(tmp_path), detected_language="en"
            )

        set_fields = mock_col.update_one.call_args[0][1]["$set"]
        assert set_fields.get("detected_language") == "en"

    def test_omits_language_field_when_not_provided(self, repo, tmp_path):
        with (
            patch("app.services.transcript_repository.videos_collection") as mock_col,
            patch("app.services.transcript_repository.upload_to_s3", return_value="http://s3/t.txt"),
        ):
            repo.save_transcription("vid1", "proj1", "job1", MOCK_SEGMENTS, str(tmp_path))

        set_fields = mock_col.update_one.call_args[0][1]["$set"]
        assert "detected_language" not in set_fields

    def test_stores_duration_when_provided(self, repo, tmp_path):
        with (
            patch("app.services.transcript_repository.videos_collection") as mock_col,
            patch("app.services.transcript_repository.upload_to_s3", return_value="http://s3/t.txt"),
        ):
            repo.save_transcription(
                "vid1", "proj1", "job1", MOCK_SEGMENTS, str(tmp_path), duration_seconds=120.5
            )

        set_fields = mock_col.update_one.call_args[0][1]["$set"]
        assert set_fields.get("duration_seconds") == 120.5
