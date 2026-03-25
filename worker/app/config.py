from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://mongodb:27017"
    S3_ENDPOINT: str = "http://minio:9000"
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    AWS_SECRET_ACCESS_KEY: str = "minioadmin"
    JWT_SECRET_KEY: str = "your_jwt_secret_key"
    BUCKET_NAME: str = "video-bucket"
    REDIS_URL: str = "redis://redis:6379/0"

    DUCK_VOLUME: float = 0.1
    ATEMPO_MIN: float = 0.75
    ATEMPO_MAX: float = 1.5
    MIX_SAMPLE_RATE: int = 48000
    AAC_BITRATE: str = "192k"
    VOICE_REF_TARGET_DURATION: float = 8.0
    VOICE_REF_MIN_CHUNK_DURATION: float = 0.5

    WHISPER_MODEL: str = "large-v3"
    WHISPER_DEVICE: str = "cuda"
    WHISPER_COMPUTE_TYPE: str = "int8"
    WHISPER_BEAM_SIZE: int = 2
    WHISPER_VAD_MIN_SILENCE_MS: int = 300
    PHRASE_GAP_THRESHOLD_MS: int = 2000

    XTTS_MODEL: str = "tts_models/multilingual/multi-dataset/xtts_v2"

    PROGRESS_TTL_SECONDS: int = 3600

    class Config:
        env_file = ".env"


settings = Settings()
