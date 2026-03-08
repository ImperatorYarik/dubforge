import os
import logging
from app.storage import client, settings

logger = logging.getLogger(__name__)


def download_file_to_disk(url: str, download_path: str) -> bool:
    """
    Extracts the object key from a full MinIO URL and downloads via boto3.
    e.g. http://minio:9000/video-bucket/proj-id/video.mp4
         -> object key: proj-id/video.mp4
    """
    try:
        base_url = settings.S3_ENDPOINT + '/' + settings.BUCKET_NAME + '/'
        object_key = url.replace(base_url, '')
        logger.info(f"Downloading object '{object_key}' to '{download_path}'")
        os.makedirs(os.path.dirname(download_path), exist_ok=True)
        client.download_file(settings.BUCKET_NAME, object_key, download_path)
        logger.info(f"Download complete: {download_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return False