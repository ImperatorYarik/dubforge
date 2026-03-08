from fastapi import APIRouter, UploadFile, File
from app.utils.storage import storage
from app.utils.youtube_metadata import get_youtube_metadata
from app.CRUD import projects


router = APIRouter()

@router.post("/create")
async def create_project(youtube_url: str):
    metadata = await get_youtube_metadata(youtube_url)
    project_id = await projects.create_project(metadata)
    storage.create_folder(project_id)
    return {"message": "Project created successfully", "metadata": metadata}

@router.get("/list_projects")
async def list_projects():
    return await projects.list_projects()