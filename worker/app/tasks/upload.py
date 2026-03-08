import logging

from app.storage import client, settings

logger = logging.getLogger(__name__)


def upload_to_s3(local_path: str, object_key: str) -> str:
    """Upload a local file to S3/MinIO and return its public URL."""
    logger.info(f"Uploading '{local_path}' → s3://{settings.BUCKET_NAME}/{object_key}")
    with open(local_path, "rb") as f:
        client.upload_fileobj(f, settings.BUCKET_NAME, object_key)
    url = f"{settings.S3_ENDPOINT}/{settings.BUCKET_NAME}/{object_key}"
    logger.info(f"Upload complete: {url}")
    return url
