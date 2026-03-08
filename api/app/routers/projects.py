from fastapi import APIRouter
from app.models.project import ProjectCreationResponse, ProjectResponse, ProjectListResponse
from app.utils.storage import storage
from app.utils.youtube_metadata import get_youtube_metadata
from app.CRUD import projects


router = APIRouter()

@router.post("/create")
async def create_project(youtube_url: str):
    metadata = await get_youtube_metadata(youtube_url)
    project_id = await projects.create_project(metadata)
    storage.create_folder(project_id)
    return ProjectCreationResponse(project_id=project_id, message="Project created successfully", metadata=metadata)

@router.get("/list_projects")
async def list_projects():
    projects_list = await projects.list_projects()
    return ProjectListResponse(projects=projects_list)

@router.get("/{project_id}")
async def get_project(project_id: str):
    project = await projects.get_project(project_id)
    if project:
        return ProjectResponse(project_id=project["project_id"], metadata=project["metadata"], created_at=project["created_at"], updated_at=project["updated_at"])
    else:
        return {"message": "Project not found"}