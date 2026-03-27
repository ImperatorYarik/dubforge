import boto3
from app.config import settings

_client = boto3.client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name="us-east-1",
)


class Storage:
    @staticmethod
    def create_bucket(bucket_name: str) -> bool:
        try:
            _client.create_bucket(Bucket=bucket_name)
            return True
        except Exception as e:
            print(f"Error creating bucket: {e}")
            return False

    @staticmethod
    def create_folder(folder_name: str) -> bool:
        try:
            _client.put_object(Bucket=settings.BUCKET_NAME, Key=f"{folder_name}/")
            return True
        except Exception as e:
            print(f"Error creating folder: {e}")
            return False

    @staticmethod
    def upload_file(file, object_name: str) -> bool:
        try:
            _client.upload_fileobj(file.file, settings.BUCKET_NAME, object_name)
            return True
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False

    @staticmethod
    def upload_file_raw(file_obj, object_name: str) -> bool:
        try:
            _client.upload_fileobj(file_obj, settings.BUCKET_NAME, object_name)
            return True
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False

    @staticmethod
    def generate_presigned_url(object_name: str, expires_in: int = 3600) -> str:
        """Return a presigned GET URL valid for `expires_in` seconds."""
        return _client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.BUCKET_NAME, "Key": object_name},
            ExpiresIn=expires_in,
        )

    @staticmethod
    def object_exists(object_name: str) -> bool:
        try:
            _client.head_object(Bucket=settings.BUCKET_NAME, Key=object_name)
            return True
        except Exception:
            return False

    @staticmethod
    def delete_object(object_name: str) -> bool:
        try:
            _client.delete_object(Bucket=settings.BUCKET_NAME, Key=object_name)
            return True
        except Exception as e:
            print(f"Error deleting object: {e}")
            return False

    @staticmethod
    def delete_folder(folder_name: str) -> bool:
        try:
            response = _client.list_objects_v2(
                Bucket=settings.BUCKET_NAME, Prefix=f"{folder_name}/"
            )
            if "Contents" in response:
                for obj in response["Contents"]:
                    _client.delete_object(Bucket=settings.BUCKET_NAME, Key=obj["Key"])
            return True
        except Exception as e:
            print(f"Error deleting folder: {e}")
            return False

    @staticmethod
    def get_base_url() -> str:
        return f"{settings.S3_ENDPOINT}/{settings.BUCKET_NAME}"


storage = Storage()
