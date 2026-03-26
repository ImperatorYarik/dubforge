from datetime import datetime

from pydantic import BaseModel


class ProjectCreationResponse(BaseModel):
    project_id: str
    message: str
    metadata: dict


class ProjectResponse(BaseModel):
    project_id: str
    metadata: dict
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
