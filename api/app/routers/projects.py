import os

from fastapi import APIRouter
from app.models.project import ProjectCreationResponse, ProjectResponse, ProjectListResponse
from app.utils.storage import storage
from app.utils.youtube_metadata import get_youtube_metadata, download_youtube_video
from app.CRUD import projects, videos

router = APIRouter()

@router.post("/create")
async def create_project(youtube_url: str, download_from_youtube: bool = True):
    metadata = await get_youtube_metadata(youtube_url)
    project_id = await projects.create_project(metadata)
    storage.create_folder(project_id)

    local_path = f"/tmp/{project_id}/video.mp4"

    if download_from_youtube:
        os.makedirs(f"/tmp/{project_id}", exist_ok=True)
        success = await download_youtube_video(youtube_url, local_path)
        if not success:
            raise RuntimeError("Failed to download YouTube video")

        object_name = f"{project_id}/video.mp4"
        with open(local_path, "rb") as f:
            storage.upload_file_raw(f, object_name)

        video_url = f"{storage.get_base_url()}/{object_name}"
        await videos.add_video(project_id, video_url)

        return ProjectCreationResponse(project_id=project_id, message="Project created successfully", metadata=metadata)


    return ProjectCreationResponse(project_id=project_id, message="Project created successfully", metadata=metadata)

@router.post("/create-blank")
async def create_blank_project(title: str = "Untitled project"):
    metadata = {"title": title}
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
    
@router.delete("/{project_id}")
async def delete_project(project_id: str):
    success = await projects.delete_project(project_id)
    if success:
        storage.delete_folder(project_id)
        return {"message": "Project deleted successfully"}
    else:
        return {"message": "Project not found"} 