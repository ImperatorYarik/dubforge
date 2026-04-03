---
name: api-error-handling
description: This skill should be used when implementing error handling for FastAPI routes, raising exceptions from repos or services, translating domain errors to HTTP responses, or ensuring consistent error response shapes.
version: 1.0.0
---

# API Error Handling

## Rule: Errors Flow Through Layers

Each layer has a specific exception type — never leak HTTP concerns into services/repos or domain errors directly to the client.

| Layer | Raises | Never raises |
|---|---|---|
| Repository | `ValueError`, domain-specific exceptions | `HTTPException` |
| Service | Domain exceptions (re-raised from repo or own logic) | `HTTPException` |
| Router | `HTTPException` (translated from domain errors) | Raw `ValueError` to client |

## Error Response Shape

Always use FastAPI's standard `{"detail": "..."}` shape — it's automatic with `HTTPException`:
```python
raise HTTPException(status_code=404, detail="Video not found")
raise HTTPException(status_code=400, detail="Invalid project ID")
raise HTTPException(status_code=500, detail="Storage service unavailable")
```

## Translation Pattern (Router)

```python
@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: str):
    try:
        video = await videos_repo.get_video(video_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unexpected error")
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return video
```

## Repository Pattern

```python
async def get_video(self, video_id: str) -> dict:
    doc = await self.collection.find_one({"video_id": video_id})
    if doc is None:
        raise ValueError(f"Video {video_id!r} not found")
    return doc
```

## Service Pattern

```python
async def enrich_result(job_result: dict) -> dict:
    try:
        url = storage.get_presigned_url(job_result["s3_key"])
    except Exception as exc:
        raise RuntimeError(f"Failed to generate presigned URL: {exc}") from exc
    return {**job_result, "url": url}
```

## Common Status Codes

| Situation | Status |
|---|---|
| Resource not found | 404 |
| Bad input / validation failure | 400 or 422 (FastAPI auto-422 for Pydantic) |
| Unauthorized | 401 |
| Forbidden | 403 |
| Unhandled server error | 500 |
