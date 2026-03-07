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
    def upload_file(file, bucket_name, object_name):
        try:
            client.upload_fileobj(file.file, bucket_name, object_name)
            return True
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False
        
    @staticmethod
    def create_bucket(bucket_name):
        try:
            client.create_bucket(Bucket=bucket_name)
            return True
        except Exception as e:
            print(f"Error creating bucket: {e}")
            return False
        
storage = Storage()