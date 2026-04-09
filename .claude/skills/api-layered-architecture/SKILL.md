---
name: api-layered-architecture
description: This skill should be used when adding new API layers (routers, repos, services, models), deciding where business logic belongs, enforcing separation of concerns, or reviewing whether code is in the right layer.
version: 1.0.0
---

# API Layered Architecture

## Layer Responsibilities

### Routers (`routers/`)
- Only handle HTTP concerns: parse request, call service/repo, return response.
- Use `HTTPException` for error responses.
- Declare `response_model` and `status_code` on every route decorator.
- Use `APIRouter` with `prefix` and `tags`; register in `main.py`.
- Use dependency injection (`Depends`) for shared resources.
- **No business logic. No direct DB calls.**

### Repositories (`repositories/`)
- All MongoDB access via Motor async.
- Encapsulate all query logic. Return domain dicts or `None`.
- Raise `ValueError` or domain-specific exceptions for not-found / validation errors — never `HTTPException`.
- Use `async def` for all methods.
- **No HTTP concerns. No Celery/MinIO calls.**

### Services (`services/`)
- Orchestrate across repos and external systems (Celery, MinIO, Redis).
- Contain business logic. Catch repo exceptions, re-raise as domain errors.
- **No HTTP concerns (no status codes, no Request/Response).**

### Models (`models/`)
- Pydantic v2 schemas for request validation and response serialization.
- Separate input schemas (request bodies) from output schemas (response models) when shapes differ.
- **No logic, no DB access.**

## Anti-Patterns (never do these)

| Anti-pattern | Fix |
|---|---|
| DB call directly in a router | Move to a repository method |
| `HTTPException` raised from a repo or service | Raise a domain exception; router translates it |
| Business logic in a router | Move to a service function |
| Motor call in a service | Delegate to the repository layer |
| Hardcoded collection names or endpoints | Use constants or `config.py` |

## File Registration

- Every new router must be imported and registered in `main.py`.
- Every new model must be importable from `models/`.
- Use constants for collection names — never inline strings in repo queries.

## Code Quality

- Type-annotate all function signatures (parameters and return types).
- Write docstrings for all public functions and classes.
- Keep functions ≤30 lines as a guideline — single purpose.
- No magic strings/numbers — use constants or config values.
