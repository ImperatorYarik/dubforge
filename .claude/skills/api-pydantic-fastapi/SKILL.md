---
name: api-pydantic-fastapi
description: This skill should be used when designing Pydantic v2 request/response schemas, using FastAPI dependency injection, declaring route decorators, structuring APIRouters, or applying FastAPI best practices for this project.
version: 1.0.0
---

# Pydantic v2 + FastAPI Patterns

## Pydantic v2 Conventions

- Use Pydantic v2 syntax: `model_config`, `model_validator`, `field_validator`.
- Separate **input schemas** (request bodies) from **output schemas** (response models) when shapes differ.
- Use `Optional[T]` with explicit `None` defaults for nullable fields.
- Use `Field(...)` with `description` for API documentation.
- Validate IDs as strings — never expose internal MongoDB `_id`.

```python
from pydantic import BaseModel, Field
from typing import Optional


class VideoCreate(BaseModel):
    project_id: str = Field(..., description="Parent project ID")
    filename: str = Field(..., description="Original filename")


class VideoResponse(BaseModel):
    video_id: str
    project_id: str
    video_url: Optional[str] = None
    dubbed_url: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}
```

## FastAPI Route Decorators

Always declare `response_model`, `status_code`, `summary`, and `tags` on routes:

```python
from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/videos", tags=["videos"])

@router.post("/", response_model=VideoResponse, status_code=status.HTTP_201_CREATED,
             summary="Upload a new video")
async def upload_video(payload: VideoCreate) -> VideoResponse:
    ...

@router.get("/{video_id}", response_model=VideoResponse, status_code=status.HTTP_200_OK,
            summary="Get video by ID")
async def get_video(video_id: str) -> VideoResponse:
    ...
```

## Dependency Injection

Use `Depends` for shared resources (DB client, settings, auth):

```python
from fastapi import Depends
from app.utils.database import get_db
from app.config import Settings, get_settings

@router.get("/")
async def list_videos(
    db=Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    ...
```

## Router Registration

Every new router must be registered in `main.py`:

```python
from app.routers import videos, projects, jobs, tts

app.include_router(videos.router)
app.include_router(projects.router)
app.include_router(jobs.router)
app.include_router(tts.router)
```

## Model Field Naming

- Use `snake_case` for all field names (Python convention, FastAPI handles serialization).
- Use descriptive names — avoid abbreviations (`project_id` not `pid`).
- Timestamp fields: `created_at`, `updated_at` as ISO strings or `datetime`.
