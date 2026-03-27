import os
import tempfile

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.storage import storage
from app.repositories import projects as projects_repo
from app.repositories import videos as videos_repo
from app.schemas.project import ProjectCreationResponse, ProjectListResponse, ProjectResponse
from app.services.youtube import download_youtube_video, get_youtube_metadata

router = APIRouter()


@router.post("/create", response_model=ProjectCreationResponse)
async def create_project(youtube_url: str, download_from_youtube: bool = True):
    metadata = await get_youtube_metadata(youtube_url)
    project_id = await projects_repo.create_project(metadata)
    storage.create_folder(project_id)

    if download_from_youtube:
        tmp_dir = os.path.join(tempfile.gettempdir(), project_id)
        local_path = os.path.join(tmp_dir, "video.mp4")
        os.makedirs(tmp_dir, exist_ok=True)
        success = await download_youtube_video(youtube_url, local_path)
        if not success:
            raise RuntimeError("Failed to download YouTube video")

        object_name = f"{project_id}/video.mp4"
        with open(local_path, "rb") as f:
            storage.upload_file_raw(f, object_name)

        video_url = f"{storage.get_base_url()}/{object_name}"
        await videos_repo.add_video(project_id, video_url)

    return ProjectCreationResponse(
        project_id=project_id,
        message="Project created successfully",
        metadata=metadata,
    )


@router.post("/create-blank", response_model=ProjectCreationResponse)
async def create_blank_project(title: str = "Untitled project"):
    metadata = {"title": title}
    project_id = await projects_repo.create_project(metadata)
    storage.create_folder(project_id)
    return ProjectCreationResponse(
        project_id=project_id,
        message="Project created successfully",
        metadata=metadata,
    )


@router.get("/list_projects", response_model=ProjectListResponse)
async def list_projects():
    return ProjectListResponse(projects=await projects_repo.list_projects())


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    project = await projects_repo.get_project(project_id)
    if not project:
        return JSONResponse(content={"message": "Project not found"})
    return ProjectResponse(**project)


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    success = await projects_repo.delete_project(project_id)
    if not success:
        return {"message": "Project not found"}
    storage.delete_folder(project_id)
    return {"message": "Project deleted successfully"}
