from pydantic import BaseModel

class VideoUploadResponse(BaseModel):
    project_id: str
    message: str
    upload_url: str