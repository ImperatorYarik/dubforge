import uuid
from datetime import datetime

from app.core.database import projects_collection


async def create_project(metadata: dict) -> str:
    project_id = str(uuid.uuid4())
    await projects_collection.insert_one({
        "project_id": project_id,
        "metadata": metadata,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    })
    return project_id


async def list_projects() -> list[dict]:
    projects = []
    async for project in projects_collection.find():
        projects.append({
            "project_id": project["project_id"],
            "metadata": project["metadata"],
            "created_at": project["created_at"],
            "updated_at": project["updated_at"],
        })
    return projects


async def get_project(project_id: str) -> dict | None:
    project = await projects_collection.find_one({"project_id": project_id})
    if not project:
        return None
    return {
        "project_id": project["project_id"],
        "metadata": project["metadata"],
        "created_at": project["created_at"],
        "updated_at": project["updated_at"],
    }


async def delete_project(project_id: str) -> bool:
    result = await projects_collection.delete_one({"project_id": project_id})
    return result.deleted_count > 0
