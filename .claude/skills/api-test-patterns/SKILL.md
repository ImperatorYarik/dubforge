---
name: api-test-patterns
description: This skill should be used when writing pytest tests for FastAPI endpoints — covering file naming, class/method naming, mocking rules, required coverage per endpoint, and the test template.
version: 1.0.0
---

# API Test Patterns

## File Naming

| What | File pattern |
|---|---|
| Router tests | `tests/test_routers_<name>.py` |
| Repository/CRUD tests | `tests/test_crud_<name>.py` |
| Utility tests | `tests/test_<util>.py` |

## Class and Method Naming

- **Class**: group by endpoint — `class TestCreateProject:`, `class TestListVideos:`
- **Method**: `test_success`, `test_returns_404_when_not_found`, `test_raises_on_db_error`

## Mocking Rules

- Mock at the **router boundary** — patch the dependency the router calls directly (e.g. `app.routers.projects.projects_repo`), not the underlying Motor call.
- Use `unittest.mock.AsyncMock` for coroutines, `MagicMock` for sync callables.
- Use `patch` as a context manager with `with (...):` grouping for multiple patches.
- Never mock `TestClient` itself — it uses the real FastAPI app.

## Mandatory Coverage Per Endpoint

Every endpoint must have tests for:
1. **Happy path** — correct status code and response shape
2. **Side effects** — verify mocked dependencies were called with the right args
3. **Error paths** — 404 when resource missing, 400/422 on bad input, 500 on service failure

## Test Template

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


MOCK_THING = {"id": "abc", "name": "test"}


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


class TestCreateThing:
    def test_success(self, client):
        with patch("app.routers.things.repo") as mock_repo:
            mock_repo.create = AsyncMock(return_value="abc")
            response = client.post("/things/", json={"name": "test"})
        assert response.status_code == 200
        assert response.json()["id"] == "abc"

    def test_returns_422_on_missing_field(self, client):
        response = client.post("/things/", json={})
        assert response.status_code == 422

    def test_calls_repo_with_correct_args(self, client):
        with patch("app.routers.things.repo") as mock_repo:
            mock_repo.create = AsyncMock(return_value="abc")
            client.post("/things/", json={"name": "test"})
        mock_repo.create.assert_called_once()
        call_args = mock_repo.create.call_args[0][0]
        assert call_args["name"] == "test"

    def test_returns_404_when_not_found(self, client):
        with patch("app.routers.things.repo") as mock_repo:
            mock_repo.get = AsyncMock(return_value=None)
            response = client.get("/things/missing-id")
        assert response.status_code == 404

    def test_returns_500_on_service_failure(self, client):
        with patch("app.routers.things.repo") as mock_repo:
            mock_repo.create = AsyncMock(side_effect=Exception("db error"))
            response = client.post("/things/", json={"name": "test"})
        assert response.status_code == 500
```

## What NOT to Test

- Implementation details — test behaviour, not internal method calls.
- Third-party library internals (Motor, Celery, boto3) — mock them at the boundary.
- Worker pipeline tasks directly — they require GPU/model files.
- Pure rendering with no logic.
