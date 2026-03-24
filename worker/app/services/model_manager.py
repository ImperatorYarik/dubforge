import logging

logger = logging.getLogger(__name__)


class ModelManager:
    def get_whisper(self):
        from app.tasks.transcribe import get_model
        return get_model()

    def release_whisper(self) -> None:
        from app.tasks.transcribe import release_model
        release_model()

    def get_tts(self):
        from app.tasks.tts import get_tts
        return get_tts()

    def release_tts(self) -> None:
        from app.tasks.tts import release_model
        release_model()

    def release_all(self) -> None:
        self.release_whisper()
        self.release_tts()


model_manager = ModelManager()
