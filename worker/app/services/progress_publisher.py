import redis

from app.models.progress import ProgressEvent


class ProgressPublisher:
    def __init__(self, redis_client: redis.Redis, task_id: str, ttl: int = 3600):
        self._redis = redis_client
        self._task_id = task_id
        self._ttl = ttl

    def update(self, step: str, pct: int, message: str = "") -> None:
        payload = ProgressEvent(step=step, pct=pct, message=message).to_json()
        self._redis.publish(f"job:{self._task_id}", payload)
        self._redis.setex(f"job:{self._task_id}:latest", self._ttl, payload)
