from app.utils.database import projects_collection
import uuid
from datetime import datetime


async def create_project(metadata: dict):
    project_id = str(uuid.uuid4())
    project_data = {
        "project_id": project_id,
        "metadata": metadata,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    await projects_collection.insert_one(project_data)
    return project_id

async def list_projects():
    projects = []
    async for project in projects_collection.find():
        projects.append({
            "project_id": project["project_id"],
            "metadata": project["metadata"],
            "created_at": project["created_at"],
            "updated_at": project["updated_at"]
        })
    return projects

async def get_project(project_id: str):
    project = await projects_collection.find_one({"project_id": project_id})
    if project:
        return {
            "project_id": project["project_id"],
            "metadata": project["metadata"],
            "created_at": project["created_at"],
            "updated_at": project["updated_at"]
        }
    else:
        return None
    
async def delete_project(project_id: str):
    result = await projects_collection.delete_one({"project_id": project_id})
    return result.deleted_count > 0