from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/video_db"
    S3_ENDPOINT: str = "http://minio:9000"
    # Public URL the browser uses to reach MinIO (rewrite presigned URL host)
    S3_PUBLIC_ENDPOINT: str = "http://localhost:9000"
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    AWS_SECRET_ACCESS_KEY: str = "minioadmin"
    JWT_SECRET_KEY: str = "your_jwt_secret_key"
    BUCKET_NAME: str = "video-bucket"
    REDIS_URL: str = "redis://redis:6379/0"
    ALLOWED_ORIGINS: list[str] = ["*"]


    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()