import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


class AsyncCursorMock:
    """Mimics Motor's async cursor for use in tests."""

    def __init__(self, items):
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration


@pytest.fixture(autouse=True)
def reset_crud_module():
    """Re-import CRUD module fresh for each test so patches take effect."""
    import importlib
    import app.CRUD.projects as m
    importlib.reload(m)
    yield


async def test_create_project_returns_uuid():
    with patch("app.CRUD.projects.projects_collection") as mock_col:
        mock_col.insert_one = AsyncMock()
        from app.CRUD.projects import create_project

        result = await create_project({"title": "Test"})

        assert isinstance(result, str)
        assert len(result) == 36  # UUID4 format: 8-4-4-4-12
        mock_col.insert_one.assert_called_once()


async def test_create_project_stores_correct_data():
    with patch("app.CRUD.projects.projects_collection") as mock_col:
        mock_col.insert_one = AsyncMock()
        from app.CRUD.projects import create_project

        metadata = {"title": "My Video", "duration": 120}
        result = await create_project(metadata)

        inserted_doc = mock_col.insert_one.call_args[0][0]
        assert inserted_doc["project_id"] == result
        assert inserted_doc["metadata"] == metadata
        assert "created_at" in inserted_doc
        assert "updated_at" in inserted_doc
        assert isinstance(inserted_doc["created_at"], datetime)


async def test_list_projects_empty():
    with patch("app.CRUD.projects.projects_collection") as mock_col:
        mock_col.find.return_value = AsyncCursorMock([])
        from app.CRUD.projects import list_projects

        result = await list_projects()

        assert result == []


async def test_list_projects_returns_all_documents():
    now = datetime.now()
    docs = [
        {"project_id": "id-1", "metadata": {"title": "A"}, "created_at": now, "updated_at": now},
        {"project_id": "id-2", "metadata": {"title": "B"}, "created_at": now, "updated_at": now},
    ]
    with patch("app.CRUD.projects.projects_collection") as mock_col:
        mock_col.find.return_value = AsyncCursorMock(docs)
        from app.CRUD.projects import list_projects

        result = await list_projects()

        assert len(result) == 2
        assert result[0]["project_id"] == "id-1"
        assert result[1]["project_id"] == "id-2"


async def test_list_projects_maps_fields_correctly():
    now = datetime.now()
    doc = {
        "_id": "mongo-internal-id",
        "project_id": "abc",
        "metadata": {"title": "Test"},
        "created_at": now,
        "updated_at": now,
    }
    with patch("app.CRUD.projects.projects_collection") as mock_col:
        mock_col.find.return_value = AsyncCursorMock([doc])
        from app.CRUD.projects import list_projects

        result = await list_projects()

        assert "_id" not in result[0]
        assert result[0]["metadata"] == {"title": "Test"}


async def test_get_project_found():
    now = datetime.now()
    doc = {"project_id": "abc", "metadata": {"title": "T"}, "created_at": now, "updated_at": now}
    with patch("app.CRUD.projects.projects_collection") as mock_col:
        mock_col.find_one = AsyncMock(return_value=doc)
        from app.CRUD.projects import get_project

        result = await get_project("abc")

        assert result is not None
        assert result["project_id"] == "abc"
        mock_col.find_one.assert_called_once_with({"project_id": "abc"})


async def test_get_project_not_found():
    with patch("app.CRUD.projects.projects_collection") as mock_col:
        mock_col.find_one = AsyncMock(return_value=None)
        from app.CRUD.projects import get_project

        result = await get_project("nonexistent")

        assert result is None
