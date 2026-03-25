import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.fixture
def client():
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


def _make_system_resp(
    gpu_available=True,
    worker_online=True,
    whisper_loaded=True,
    xtts_loaded=False,
    active_jobs=0,
    queued_jobs=0,
):
    return {
        "gpu_available": gpu_available,
        "gpu_name": "NVIDIA RTX 3090" if gpu_available else None,
        "gpu_memory_used_mb": 4096 if gpu_available else 0,
        "gpu_memory_total_mb": 24576 if gpu_available else 0,
        "whisper_loaded": whisper_loaded,
        "xtts_loaded": xtts_loaded,
        "worker_online": worker_online,
        "active_jobs": active_jobs,
        "queued_jobs": queued_jobs,
    }


class TestSystemStatus:
    def test_returns_correct_shape(self, client):
        with (
            patch("app.routers.system._gpu_info", return_value={
                "available": True, "name": "RTX 3090", "used_mb": 4096, "total_mb": 24576,
            }),
            patch("app.routers.system.aioredis") as mock_redis_mod,
            patch("app.routers.system.celery") as mock_celery,
        ):
            mock_r = AsyncMock()
            mock_r.get = AsyncMock(side_effect=[b"1", b"0"])
            mock_r.aclose = AsyncMock()
            mock_redis_mod.from_url.return_value = mock_r

            mock_inspect = MagicMock()
            mock_inspect.ping.return_value = {"worker@host": {"ok": "pong"}}
            mock_inspect.active.return_value = {}
            mock_inspect.reserved.return_value = {}
            mock_celery.control.inspect.return_value = mock_inspect

            resp = client.get("/system/status")

        assert resp.status_code == 200
        data = resp.json()
        required_keys = [
            "gpu_available", "gpu_name", "gpu_memory_used_mb", "gpu_memory_total_mb",
            "whisper_loaded", "xtts_loaded", "worker_online", "active_jobs", "queued_jobs",
        ]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"

    def test_worker_offline_case(self, client):
        with (
            patch("app.routers.system._gpu_info", return_value={
                "available": False, "name": None, "used_mb": 0, "total_mb": 0,
            }),
            patch("app.routers.system.aioredis") as mock_redis_mod,
            patch("app.routers.system.celery") as mock_celery,
        ):
            mock_r = AsyncMock()
            mock_r.get = AsyncMock(return_value=None)
            mock_r.aclose = AsyncMock()
            mock_redis_mod.from_url.return_value = mock_r

            # Simulate worker timeout
            mock_celery.control.inspect.side_effect = Exception("Connection refused")

            resp = client.get("/system/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["worker_online"] is False
        assert data["gpu_available"] is False

    def test_gpu_not_available(self, client):
        with (
            patch("app.routers.system._gpu_info", return_value={
                "available": False, "name": None, "used_mb": 0, "total_mb": 0,
            }),
            patch("app.routers.system.aioredis") as mock_redis_mod,
            patch("app.routers.system.celery") as mock_celery,
        ):
            mock_r = AsyncMock()
            mock_r.get = AsyncMock(return_value=None)
            mock_r.aclose = AsyncMock()
            mock_redis_mod.from_url.return_value = mock_r

            mock_inspect = MagicMock()
            mock_inspect.ping.return_value = None
            mock_celery.control.inspect.return_value = mock_inspect

            resp = client.get("/system/status")

        data = resp.json()
        assert data["gpu_available"] is False
        assert data["gpu_name"] is None
        assert data["gpu_memory_used_mb"] == 0

    def test_whisper_loaded_from_redis(self, client):
        with (
            patch("app.routers.system._gpu_info", return_value={
                "available": True, "name": "RTX A6000", "used_mb": 8192, "total_mb": 49152,
            }),
            patch("app.routers.system.aioredis") as mock_redis_mod,
            patch("app.routers.system.celery") as mock_celery,
        ):
            mock_r = AsyncMock()
            # whisper=1 (loaded), xtts=0 (not loaded)
            mock_r.get = AsyncMock(side_effect=[b"1", b"0"])
            mock_r.aclose = AsyncMock()
            mock_redis_mod.from_url.return_value = mock_r

            mock_inspect = MagicMock()
            mock_inspect.ping.return_value = {"w@h": {"ok": "pong"}}
            mock_inspect.active.return_value = {}
            mock_inspect.reserved.return_value = {}
            mock_celery.control.inspect.return_value = mock_inspect

            resp = client.get("/system/status")

        data = resp.json()
        assert data["whisper_loaded"] is True
        assert data["xtts_loaded"] is False

    def test_active_jobs_count(self, client):
        with (
            patch("app.routers.system._gpu_info", return_value={
                "available": True, "name": "GPU", "used_mb": 0, "total_mb": 0,
            }),
            patch("app.routers.system.aioredis") as mock_redis_mod,
            patch("app.routers.system.celery") as mock_celery,
        ):
            mock_r = AsyncMock()
            mock_r.get = AsyncMock(return_value=None)
            mock_r.aclose = AsyncMock()
            mock_redis_mod.from_url.return_value = mock_r

            mock_inspect = MagicMock()
            mock_inspect.ping.return_value = {"worker@host": {"ok": "pong"}}
            # 2 active tasks on one worker
            mock_inspect.active.return_value = {"worker@host": [{"id": "t1"}, {"id": "t2"}]}
            mock_inspect.reserved.return_value = {"worker@host": [{"id": "t3"}]}
            mock_celery.control.inspect.return_value = mock_inspect

            resp = client.get("/system/status")

        data = resp.json()
        assert data["active_jobs"] == 2
        assert data["queued_jobs"] == 1
