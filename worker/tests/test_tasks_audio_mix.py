import pytest
from unittest.mock import patch, MagicMock
from app.tasks.audio_mix import build_atempo_filter, stretch_clip, build_dubbed_audio, mux_audio_into_video
from app.models.segment import TranscriptSegment


class TestBuildAtempoFilter:
    def test_simple_ratio_within_range(self):
        result = build_atempo_filter(1.0)
        assert result == "atempo=1.000000"

    def test_ratio_at_upper_boundary(self):
        result = build_atempo_filter(2.0)
        # Should not chain extra filters for exactly 2.0
        assert result == "atempo=2.000000"

    def test_ratio_at_lower_boundary(self):
        result = build_atempo_filter(0.5)
        assert result == "atempo=0.500000"

    def test_ratio_above_2_chains_filters(self):
        result = build_atempo_filter(4.0)
        filters = result.split(",")
        assert "atempo=2.0" in filters
        assert len(filters) == 2

    def test_ratio_above_4_chains_multiple_filters(self):
        result = build_atempo_filter(8.0)
        filters = result.split(",")
        assert filters.count("atempo=2.0") == 2
        assert len(filters) == 3

    def test_ratio_below_0_5_chains_filters(self):
        result = build_atempo_filter(0.25)
        filters = result.split(",")
        assert "atempo=0.5" in filters
        assert len(filters) == 2

    def test_result_contains_final_remainder_filter(self):
        result = build_atempo_filter(3.0)
        filters = result.split(",")
        # 3.0 → one atempo=2.0, remainder = 1.5
        assert "atempo=2.0" in filters
        last = filters[-1]
        assert last.startswith("atempo=")
        assert "1.5" in last


class TestStretchClip:
    def test_returns_true_on_success(self, tmp_path):
        input_wav = str(tmp_path / "input.wav")
        output_wav = str(tmp_path / "output.wav")

        with (
            patch("app.tasks.audio_mix.get_duration", return_value=5.0),
            patch("app.tasks.audio_mix.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            result = stretch_clip(input_wav, output_wav, target_duration=5.0)

        assert result is True

    def test_returns_false_on_ffmpeg_failure(self, tmp_path):
        input_wav = str(tmp_path / "input.wav")
        output_wav = str(tmp_path / "output.wav")

        with (
            patch("app.tasks.audio_mix.get_duration", return_value=5.0),
            patch("app.tasks.audio_mix.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=1, stderr=b"error")
            result = stretch_clip(input_wav, output_wav, target_duration=5.0)

        assert result is False

    def test_clamps_ratio_to_max(self, tmp_path):
        input_wav = str(tmp_path / "input.wav")
        output_wav = str(tmp_path / "output.wav")
        captured_cmd = []

        def capture_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            return MagicMock(returncode=0)

        with (
            patch("app.tasks.audio_mix.get_duration", return_value=10.0),
            patch("app.tasks.audio_mix.subprocess.run", side_effect=capture_run),
        ):
            # src=10s, target=5s → ratio=2.0, max=1.5 → clamped to 1.5
            stretch_clip(input_wav, output_wav, target_duration=5.0, atempo_min=0.75, atempo_max=1.5)

        filter_str = " ".join(captured_cmd)
        assert "atempo=1.500000" in filter_str

    def test_clamps_ratio_to_min(self, tmp_path):
        input_wav = str(tmp_path / "input.wav")
        output_wav = str(tmp_path / "output.wav")
        captured_cmd = []

        def capture_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            return MagicMock(returncode=0)

        with (
            patch("app.tasks.audio_mix.get_duration", return_value=1.0),
            patch("app.tasks.audio_mix.subprocess.run", side_effect=capture_run),
        ):
            # src=1s, target=5s → ratio=0.2, min=0.75 → clamped to 0.75
            stretch_clip(input_wav, output_wav, target_duration=5.0, atempo_min=0.75, atempo_max=1.5)

        filter_str = " ".join(captured_cmd)
        assert "atempo=0.750000" in filter_str


class TestBuildDubbedAudio:
    def _make_segment_with_tts(self, start, end, text, tts_wav):
        seg = TranscriptSegment(start=start, end=end, text=text, tts_wav=tts_wav)
        return seg

    def test_returns_true_on_success(self, tmp_path):
        segments = [self._make_segment_with_tts(0.0, 5.0, "Hello", "/tmp/tts_0.wav")]
        with (
            patch("app.tasks.audio_mix.get_duration", return_value=10.0),
            patch("app.tasks.audio_mix.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            result = build_dubbed_audio("/tmp/bg.wav", segments, str(tmp_path / "out.wav"))

        assert result is True

    def test_returns_false_on_ffmpeg_failure(self, tmp_path):
        segments = [self._make_segment_with_tts(0.0, 5.0, "Hello", "/tmp/tts_0.wav")]
        with (
            patch("app.tasks.audio_mix.get_duration", return_value=10.0),
            patch("app.tasks.audio_mix.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=1, stderr=b"error")
            result = build_dubbed_audio("/tmp/bg.wav", segments, str(tmp_path / "out.wav"))

        assert result is False

    def test_builds_command_with_ducking_enabled(self, tmp_path):
        segments = [self._make_segment_with_tts(1.0, 3.0, "Hello", "/tmp/tts_0.wav")]
        captured_cmd = []

        def capture_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            return MagicMock(returncode=0)

        with (
            patch("app.tasks.audio_mix.get_duration", return_value=10.0),
            patch("app.tasks.audio_mix.subprocess.run", side_effect=capture_run),
        ):
            build_dubbed_audio("/tmp/bg.wav", segments, str(tmp_path / "out.wav"), duck_volume=0.1, ducking_enabled=True)

        filter_str = " ".join(captured_cmd)
        assert "volume=" in filter_str

    def test_no_ducking_uses_acopy(self, tmp_path):
        segments = [self._make_segment_with_tts(1.0, 3.0, "Hello", "/tmp/tts_0.wav")]
        captured_cmd = []

        def capture_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            return MagicMock(returncode=0)

        with (
            patch("app.tasks.audio_mix.get_duration", return_value=10.0),
            patch("app.tasks.audio_mix.subprocess.run", side_effect=capture_run),
        ):
            build_dubbed_audio("/tmp/bg.wav", segments, str(tmp_path / "out.wav"), ducking_enabled=False)

        filter_str = " ".join(captured_cmd)
        assert "acopy" in filter_str


class TestMuxAudioIntoVideo:
    def test_returns_true_on_success(self, tmp_path):
        with patch("app.tasks.audio_mix.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = mux_audio_into_video("/tmp/video.mp4", "/tmp/audio.wav", str(tmp_path / "out.mp4"))
        assert result is True

    def test_returns_false_on_failure(self, tmp_path):
        with patch("app.tasks.audio_mix.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr=b"error")
            result = mux_audio_into_video("/tmp/video.mp4", "/tmp/audio.wav", str(tmp_path / "out.mp4"))
        assert result is False

    def test_command_copies_video_stream(self, tmp_path):
        captured_cmd = []

        def capture_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            return MagicMock(returncode=0)

        with patch("app.tasks.audio_mix.subprocess.run", side_effect=capture_run):
            mux_audio_into_video("/tmp/video.mp4", "/tmp/audio.wav", str(tmp_path / "out.mp4"))

        assert "-c:v" in captured_cmd
        idx = captured_cmd.index("-c:v")
        assert captured_cmd[idx + 1] == "copy"
