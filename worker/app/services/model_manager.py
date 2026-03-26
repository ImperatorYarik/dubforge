import logging
import redis as sync_redis
from app.config import settings

logger = logging.getLogger(__name__)

_redis = sync_redis.from_url(settings.REDIS_URL)


class ModelManager:
    def get_whisper(self):
        from app.tasks.transcribe import get_model
        model = get_model()
        _redis.set("model:whisper:loaded", "1")
        return model

    def release_whisper(self) -> None:
        from app.tasks.transcribe import release_model
        release_model()
        _redis.set("model:whisper:loaded", "0")

    def get_tts(self):
        from app.tasks.tts import get_tts
        model = get_tts()
        _redis.set("model:xtts:loaded", "1")
        return model

    def release_tts(self) -> None:
        from app.tasks.tts import release_model
        release_model()
        _redis.set("model:xtts:loaded", "0")

    def release_all(self) -> None:
        self.release_whisper()
        self.release_tts()


model_manager = ModelManager()
