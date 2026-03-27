import json
import pytest
from pydantic import ValidationError
from app.models.job import JobContext, DubJobResult, TranscribeJobResult, TtsJobResult, SeparateJobResult
from app.models.audio import SeparationResult, VoiceReferenceResult
from app.models.progress import ProgressEvent
from app.models.segment import TranscriptSegment, WordTimestamp


class TestJobContext:
    def test_valid_context(self):
        ctx = JobContext(
            project_id="p1",
            video_id="v1",
            input_url="http://minio/bucket/video.mp4",
            job_id="j1",
            tmp_dir="/tmp/j1",
        )
        assert ctx.project_id == "p1"
        assert ctx.video_id == "v1"
        assert ctx.job_id == "j1"

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            JobContext(project_id="p1", video_id="v1", input_url="url", job_id="j1")


class TestDubJobResult:
    def test_valid_result(self):
        result = DubJobResult(
            status="completed",
            dubbed_url="http://s3/dubbed.mp4",
            transcript_url="http://s3/transcript.txt",
            vocals_url="http://s3/vocals.wav",
            no_vocals_url="http://s3/no_vocals.wav",
            video_id="v1",
        )
        assert result.status == "completed"
        assert result.video_id == "v1"

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            DubJobResult(status="completed", dubbed_url="url", transcript_url="url")


class TestTranscribeJobResult:
    def test_valid_result(self):
        result = TranscribeJobResult(
            status="completed",
            video_id="v1",
            transcript_url="http://s3/transcript.txt",
        )
        assert result.transcript_url == "http://s3/transcript.txt"

    def test_missing_video_id_raises(self):
        with pytest.raises(ValidationError):
            TranscribeJobResult(status="completed", transcript_url="url")


class TestTtsJobResult:
    def test_valid_result(self):
        result = TtsJobResult(audio_url="http://s3/audio.wav", format="wav")
        assert result.format == "wav"

    def test_mp3_format(self):
        result = TtsJobResult(audio_url="http://s3/audio.mp3", format="mp3")
        assert result.format == "mp3"

    def test_missing_format_raises(self):
        with pytest.raises(ValidationError):
            TtsJobResult(audio_url="http://s3/audio.wav")


class TestSeparateJobResult:
    def test_valid_result(self):
        result = SeparateJobResult(
            status="completed",
            video_id="v1",
            vocals_url="http://s3/vocals.wav",
            no_vocals_url="http://s3/no_vocals.wav",
        )
        assert result.status == "completed"

    def test_missing_urls_raises(self):
        with pytest.raises(ValidationError):
            SeparateJobResult(status="completed", video_id="v1")


class TestSeparationResult:
    def test_valid_result(self):
        result = SeparationResult(vocals_path="/tmp/vocals.wav", no_vocals_path="/tmp/no_vocals.wav")
        assert result.vocals_path == "/tmp/vocals.wav"

    def test_missing_no_vocals_path_raises(self):
        with pytest.raises(ValidationError):
            SeparationResult(vocals_path="/tmp/vocals.wav")


class TestVoiceReferenceResult:
    def test_valid_result(self):
        result = VoiceReferenceResult(wav_path="/tmp/ref.wav", reference_text="Hello")
        assert result.reference_text == "Hello"

    def test_missing_fields_raise(self):
        with pytest.raises(ValidationError):
            VoiceReferenceResult(wav_path="/tmp/ref.wav")


class TestProgressEvent:
    def test_valid_event(self):
        event = ProgressEvent(step="video_dub", pct=50, message="Halfway")
        assert event.step == "video_dub"
        assert event.pct == 50
        assert event.message == "Halfway"

    def test_default_message_is_empty(self):
        event = ProgressEvent(step="video_dub", pct=0)
        assert event.message == ""

    def test_to_json_returns_valid_json(self):
        event = ProgressEvent(step="transcribe", pct=75, message="Almost done")
        payload = event.to_json()
        data = json.loads(payload)
        assert data["step"] == "transcribe"
        assert data["pct"] == 75
        assert data["message"] == "Almost done"

    def test_missing_required_fields_raise(self):
        with pytest.raises(ValidationError):
            ProgressEvent(step="video_dub")


class TestTranscriptSegment:
    def test_valid_segment(self):
        seg = TranscriptSegment(start=0.0, end=5.0, text="Hello")
        assert seg.start == 0.0
        assert seg.end == 5.0
        assert seg.words == []
        assert seg.tts_wav is None

    def test_segment_with_words(self):
        words = [WordTimestamp(word="Hello", start=0.0, end=0.5)]
        seg = TranscriptSegment(start=0.0, end=0.5, text="Hello", words=words)
        assert len(seg.words) == 1
        assert seg.words[0].word == "Hello"

    def test_segment_with_tts_wav(self):
        seg = TranscriptSegment(start=0.0, end=5.0, text="Hello", tts_wav="/tmp/tts.wav")
        assert seg.tts_wav == "/tmp/tts.wav"

    def test_missing_required_fields_raise(self):
        with pytest.raises(ValidationError):
            TranscriptSegment(start=0.0, text="Hello")


class TestWordTimestamp:
    def test_valid_word(self):
        word = WordTimestamp(word="Hello", start=0.0, end=0.5)
        assert word.word == "Hello"
        assert word.start == 0.0
        assert word.end == 0.5

    def test_missing_fields_raise(self):
        with pytest.raises(ValidationError):
            WordTimestamp(word="Hello", start=0.0)
