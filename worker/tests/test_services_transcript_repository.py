import pytest
from unittest.mock import patch
from app.models.segment import TranscriptSegment
from app.services.transcript_repository import TranscriptRepository


@pytest.fixture
def repo():
    return TranscriptRepository()


MOCK_SEGMENTS = [
    TranscriptSegment(start=0.0, end=5.0, text="Hello world"),
    TranscriptSegment(start=5.5, end=10.0, text="How are you"),
]


class TestParseExisting:
    def test_returns_none_when_no_transcription_data(self):
        result = TranscriptRepository.parse_existing(None, None)
        assert result is None

    def test_returns_none_when_empty_transcription(self):
        result = TranscriptRepository.parse_existing(None, "")
        assert result is None

    def test_parses_plain_text_format(self):
        text = "[0.00s - 5.00s] Hello world\n[5.50s - 10.00s] How are you\n"
        result = TranscriptRepository.parse_existing(None, text)

        assert result is not None
        segments, returned_text = result
        assert len(segments) == 2
        assert segments[0].start == 0.0
        assert segments[0].end == 5.0
        assert segments[0].text == "Hello world"
        assert segments[1].start == 5.5
        assert segments[1].text == "How are you"

    def test_prefers_structured_segments_over_plain_text(self):
        raw_segs = [{"start": 0.0, "end": 5.0, "text": "Structured segment"}]
        text = "[0.00s - 5.00s] Plain text\n"
        result = TranscriptRepository.parse_existing(raw_segs, text)

        segments, _ = result
        assert segments[0].text == "Structured segment"

    def test_returns_none_when_plain_text_has_no_parseable_segments(self):
        result = TranscriptRepository.parse_existing(None, "No timestamps here")
        assert result is None

    def test_returns_transcription_text_alongside_segments(self):
        text = "[0.00s - 5.00s] Hello world\n"
        result = TranscriptRepository.parse_existing(None, text)

        _, returned_text = result
        assert returned_text == text

    def test_uses_structured_segments_with_provided_transcription_text(self):
        raw_segs = [{"start": 1.0, "end": 3.0, "text": "Hi"}]
        text = "some existing text"
        result = TranscriptRepository.parse_existing(raw_segs, text)

        segments, returned_text = result
        assert returned_text == text
        assert segments[0].text == "Hi"

    def test_returns_none_when_structured_segments_list_is_empty(self):
        result = TranscriptRepository.parse_existing([], "some text")
        assert result is None


class TestSaveTranscription:
    def test_writes_transcript_file(self, repo, tmp_path):
        with patch(
            "app.services.transcript_repository.upload_to_s3", return_value="http://s3/t.txt"
        ):
            repo.save_transcription("proj1", "job1", MOCK_SEGMENTS, str(tmp_path))

        transcript_file = tmp_path / "transcription.txt"
        assert transcript_file.exists()
        content = transcript_file.read_text()
        assert "[0.00s - 5.00s] Hello world" in content
        assert "[5.50s - 10.00s] How are you" in content

    def test_uploads_to_correct_s3_key(self, repo, tmp_path):
        with patch(
            "app.services.transcript_repository.upload_to_s3", return_value="http://s3/t.txt"
        ) as mock_upload:
            repo.save_transcription("proj1", "job1", MOCK_SEGMENTS, str(tmp_path))

        mock_upload.assert_called_once()
        _, s3_key = mock_upload.call_args[0]
        assert s3_key == "proj1/transcription_job1.txt"

    def test_returns_transcript_url(self, repo, tmp_path):
        with patch(
            "app.services.transcript_repository.upload_to_s3",
            return_value="http://s3/transcript.txt",
        ):
            url = repo.save_transcription("proj1", "job1", MOCK_SEGMENTS, str(tmp_path))

        assert url == "http://s3/transcript.txt"

    def test_does_not_write_to_mongodb(self, repo, tmp_path):
        """save_transcription must not touch MongoDB — DB writes are the API's responsibility."""
        with patch(
            "app.services.transcript_repository.upload_to_s3", return_value="http://s3/t.txt"
        ):
            # No DB patch needed — any attempt to use videos_collection would
            # raise an ImportError, causing the test to fail.
            repo.save_transcription("proj1", "job1", MOCK_SEGMENTS, str(tmp_path))

    def test_accepts_detected_language_param(self, repo, tmp_path):
        with patch(
            "app.services.transcript_repository.upload_to_s3", return_value="http://s3/t.txt"
        ):
            # Should not raise — detected_language is accepted as optional kwarg
            repo.save_transcription(
                "proj1", "job1", MOCK_SEGMENTS, str(tmp_path), detected_language="en"
            )

    def test_accepts_duration_seconds_param(self, repo, tmp_path):
        with patch(
            "app.services.transcript_repository.upload_to_s3", return_value="http://s3/t.txt"
        ):
            repo.save_transcription(
                "proj1", "job1", MOCK_SEGMENTS, str(tmp_path), duration_seconds=120.5
            )
