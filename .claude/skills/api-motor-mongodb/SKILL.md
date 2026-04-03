---
name: api-motor-mongodb
description: This skill should be used when writing repository methods, performing MongoDB queries with Motor, handling upserts, preventing duplicate array entries, or designing new query patterns that require indexing.
version: 1.0.0
---

# Motor / MongoDB Patterns

## Core Rules

- Always use `async def` for repository methods — Motor is fully async.
- Use `await` on all Motor operations: `find_one`, `find`, `update_one`, `insert_one`.
- Never hardcode collection names — use constants or `config.py`.
- Validate document existence before updates — raise `ValueError` (not `HTTPException`) from repos.

## Update Patterns

**Partial updates — always use `$set`** to avoid overwriting unrelated fields:
```python
await collection.update_one(
    {"video_id": video_id},
    {"$set": {"dubbed_url": url, "updated_at": datetime.utcnow()}}
)
```

**Idempotent upsert** — create or update atomically:
```python
await collection.update_one(
    {"project_id": project_id},
    {"$set": data},
    upsert=True
)
```

**Prevent duplicate array entries** — use `$push` with `$each` + `$ne` guard (keyed on a unique field like `job_id`):
```python
await collection.update_one(
    {"video_id": video_id},
    {
        "$push": {
            "dubbed_versions": {
                "$each": [version],
                "$ne": {"job_id": version["job_id"]}
            }
        }
    }
)
```
> Note: `$ne` is not a valid `$push` modifier — for true duplicate prevention use `$addToSet` on simple values, or check existence first for subdocument arrays. The pattern used in this project is a conditional `$push` guarded by a pre-check or an upsert on the subdocument.

**Practical duplicate-safe push used in this project** (`persist_job_result` pattern):
```python
# Only push if job_id not already in array
await collection.update_one(
    {"video_id": video_id, "dubbed_versions.job_id": {"$ne": job_id}},
    {"$push": {"dubbed_versions": version_data}}
)
```

## Indexing

When adding a new query pattern, advise on index creation:
```python
# Example: index for frequent lookup by project_id + video_id
await db["videos"].create_index([("project_id", 1), ("video_id", 1)])
```

Always mention index recommendations when writing new `find_one` or `find` queries that filter on non-`_id` fields.

## Document Existence Check

```python
async def get_video(self, video_id: str) -> dict | None:
    doc = await self.collection.find_one({"video_id": video_id})
    return doc

# In router:
video = await videos_repo.get_video(video_id)
if not video:
    raise HTTPException(status_code=404, detail="Video not found")
```
