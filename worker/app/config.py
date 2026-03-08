from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    S3_ENDPOINT: str = "http://minio:9000"
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    AWS_SECRET_ACCESS_KEY: str = "minioadmin"
    JWT_SECRET_KEY: str = "your_jwt_secret_key"
    BUCKET_NAME: str = "video-bucket"
    REDIS_URL: str = "redis://redis:6379/0"


    class Config:
        env_file = ".env"

settings = Settings()