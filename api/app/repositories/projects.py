import uuid
from datetime import datetime, timezone

from sqlalchemy import select, delete

from app.core.database import AsyncSessionLocal
from app.models.project import Project


async def create_project(metadata: dict) -> str:
    project_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        async with session.begin():
            row = Project(project_id=project_id, metadata_=metadata)
            session.add(row)
    return project_id


async def list_projects() -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Project).order_by(Project.created_at))
        rows = result.scalars().all()
    return [_project_to_dict(row) for row in rows]


async def get_project(project_id: str) -> dict | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Project).where(Project.project_id == project_id)
        )
        row = result.scalar_one_or_none()
    return _project_to_dict(row) if row else None


async def delete_project(project_id: str) -> bool:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                delete(Project).where(Project.project_id == project_id)
            )
    return result.rowcount > 0


def _project_to_dict(row: Project) -> dict:
    return {
        "project_id": row.project_id,
        "metadata": row.metadata_,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
