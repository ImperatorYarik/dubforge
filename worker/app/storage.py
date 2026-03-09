import boto3
from app.config import settings

client = boto3.client(
    's3',
    endpoint_url=settings.S3_ENDPOINT,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name='us-east-1'
)

class Storage:        
    @staticmethod
    def upload_file(file, object_name):
        try:
            client.upload_fileobj(file.file, settings.BUCKET_NAME, object_name)
            return True
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False

    @staticmethod
    def upload_file_from_path(local_path: str, object_name: str) -> str:
        """Upload a local file path to S3 and return its URL."""
        with open(local_path, "rb") as f:
            client.upload_fileobj(f, settings.BUCKET_NAME, object_name)
        return f"{settings.S3_ENDPOINT}/{settings.BUCKET_NAME}/{object_name}"

    @staticmethod
    def get_base_url():
        return settings.S3_ENDPOINT + '/' + settings.BUCKET_NAME
    
    def download_file(self, object_name):
        try:
            response = client.get_object(Bucket=settings.BUCKET_NAME, Key=object_name)
            return response['Body'].read()
        except Exception as e:
            print(f"Error downloading file: {e}")
            return None
        
storage = Storage()