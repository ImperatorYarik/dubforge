import json
import pytest
from unittest.mock import MagicMock
from app.services.progress_publisher import ProgressPublisher


@pytest.fixture
def redis_client():
    return MagicMock()


@pytest.fixture
def publisher(redis_client):
    return ProgressPublisher(redis_client=redis_client, task_id="task-123", ttl=3600)


class TestProgressPublisherUpdate:
    def test_publishes_to_correct_channel(self, publisher, redis_client):
        publisher.update("video_dub", 50, "Halfway")
        redis_client.publish.assert_called_once()
        channel = redis_client.publish.call_args[0][0]
        assert channel == "job:task-123"

    def test_stores_latest_with_ttl(self, publisher, redis_client):
        publisher.update("video_dub", 50, "Halfway")
        redis_client.setex.assert_called_once()
        key, ttl, _ = redis_client.setex.call_args[0]
        assert key == "job:task-123:latest"
        assert ttl == 3600

    def test_payload_is_valid_json(self, publisher, redis_client):
        publisher.update("transcribe", 25, "Processing")
        payload = redis_client.publish.call_args[0][1]
        data = json.loads(payload)
        assert data["step"] == "transcribe"
        assert data["pct"] == 25
        assert data["message"] == "Processing"

    def test_same_payload_published_and_stored(self, publisher, redis_client):
        publisher.update("tts", 80)
        published_payload = redis_client.publish.call_args[0][1]
        stored_payload = redis_client.setex.call_args[0][2]
        assert published_payload == stored_payload

    def test_default_message_is_empty(self, publisher, redis_client):
        publisher.update("video_dub", 0)
        payload = redis_client.publish.call_args[0][1]
        data = json.loads(payload)
        assert data["message"] == ""

    def test_custom_ttl_used_for_setex(self, redis_client):
        publisher = ProgressPublisher(redis_client=redis_client, task_id="t1", ttl=120)
        publisher.update("step", 10)
        _, ttl, _ = redis_client.setex.call_args[0]
        assert ttl == 120
