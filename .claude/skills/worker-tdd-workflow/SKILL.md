---
name: worker-tdd-workflow
description: This skill should be used when writing tests for worker pipeline tasks, mocking GPU/model dependencies, testing orchestration logic and caching decisions, or following TDD for new worker features.
version: 1.0.0
---

# Worker TDD Workflow

## The Core Challenge

Worker tasks require CUDA GPUs and downloaded AI models. Tests must NEVER depend on real hardware. Mock all model/GPU dependencies at the service boundary.

## The TDD Cycle (Same as Always)

1. **RED** — Write a failing test that describes the desired behaviour. Confirm it fails with a meaningful error, not a syntax error.
2. **GREEN** — Write the minimum production code to pass the test.
3. **REFACTOR** — Clean up. Keep tests green.

For bug fixes: write a failing test reproducing the bug first, then fix.

## What to Test

Test **orchestration logic**, not AI model internals:

| What to test | How |
|---|---|
| Pipeline calls tasks in correct order | Mock each task function, assert call order |
| Caching logic | Mock `storage.object_exists` to return True/False, assert Demucs not called when cached |
| Progress publishing | Assert `publisher.publish` called at expected steps with expected `pct` |
| Error handling | Mock a task to raise, assert job state is `FAILURE` and error published |
| VRAM release | Assert `release_model` called after transcription and before XTTS load |
| Correct kwargs passed to tasks | Assert task called with `assert_called_once_with(...)` |

**Do NOT test**: Whisper transcription accuracy, XTTS audio quality, Demucs separation quality — these are model internals.

## Mock at the Service/Task Boundary

```python
from unittest.mock import MagicMock, patch, AsyncMock

def test_dubbing_pipeline_calls_demucs_when_no_cache():
    with (
        patch("app.pipelines.dubbing_pipeline.download_video") as mock_dl,
        patch("app.pipelines.dubbing_pipeline.extract_audio") as mock_extract,
        patch("app.pipelines.dubbing_pipeline.transcribe") as mock_transcribe,
        patch("app.pipelines.dubbing_pipeline.synthesise_tts") as mock_tts,
        patch("app.pipelines.dubbing_pipeline.audio_mix") as mock_mix,
        patch("app.pipelines.dubbing_pipeline.upload_results") as mock_upload,
        patch("app.pipelines.dubbing_pipeline.release_model") as mock_release,
        patch("app.pipelines.dubbing_pipeline.storage") as mock_storage,
    ):
        mock_storage.object_exists.return_value = False
        mock_dl.return_value = Path("/tmp/video.mp4")
        mock_extract.return_value = (Path("/tmp/vocals.wav"), Path("/tmp/no_vocals.wav"))
        mock_transcribe.return_value = [{"start": 0.0, "end": 2.0, "text": "Hello"}]
        mock_tts.return_value = Path("/tmp/dubbed.wav")
        mock_mix.return_value = Path("/tmp/output.mp4")
        mock_upload.return_value = {"dubbed_url": "http://minio/...", "vocals_url": "http://minio/..."}

        result = dub_video(
            video_url="http://minio/video.mp4",
            vocals_url=None,
            segments=[],
            job_id="test-job-1",
            project_id="proj-1",
            video_id="vid-1",
        )

    mock_extract.assert_called_once()   # Demucs ran because no cache
    mock_release.assert_called_once()   # Whisper released before XTTS
    assert result["dubbed_url"] == "http://minio/..."
```

## Testing the Caching Path

```python
def test_skips_demucs_when_vocals_cached():
    with (
        patch("app.pipelines.dubbing_pipeline.storage") as mock_storage,
        patch("app.pipelines.dubbing_pipeline.extract_audio") as mock_extract,
        # ... other patches ...
    ):
        mock_storage.object_exists.return_value = True  # cached!

        dub_video(
            video_url="...", vocals_url="http://minio/vocals.wav",
            segments=[], job_id="j1", project_id="p1", video_id="v1",
        )

    mock_extract.assert_not_called()  # Demucs skipped
```

## Test File Location and Naming

Worker pipeline tests go in `worker/tests/` (or `api/tests/` if testing the task-dispatch integration):

| What | File |
|---|---|
| Pipeline orchestration | `worker/tests/test_pipelines_<name>.py` |
| Individual task logic | `worker/tests/test_tasks_<name>.py` |
| Service layer | `worker/tests/test_services_<name>.py` |

## Running Worker Tests

```bash
cd worker
pip install -r requirements.txt
pytest                        # all tests
pytest tests/test_pipelines_dubbing.py
pytest -x                     # stop on first failure
pytest --tb=short
```
