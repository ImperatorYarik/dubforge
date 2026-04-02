import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


def make_mock_session():
    """Return (mock_session_local, mock_session) pair for patching AsyncSessionLocal."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    mock_begin = AsyncMock()
    mock_begin.__aenter__ = AsyncMock(return_value=None)
    mock_begin.__aexit__ = AsyncMock(return_value=False)
    mock_session.begin = MagicMock(return_value=mock_begin)

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_session_local = MagicMock(return_value=mock_ctx)
    return mock_session_local, mock_session


@pytest.fixture(autouse=True)
def reset_crud_module():
    """Re-import repository module fresh for each test so patches take effect."""
    import importlib
    import app.repositories.projects as m
    importlib.reload(m)
    yield


async def test_create_project_returns_uuid():
    mock_session_local, mock_session = make_mock_session()
    with patch("app.repositories.projects.AsyncSessionLocal", mock_session_local):
        from app.repositories.projects import create_project
        result = await create_project({"title": "Test"})

    assert isinstance(result, str)
    assert len(result) == 36  # UUID4 format: 8-4-4-4-12
    mock_session.add.assert_called_once()


async def test_create_project_stores_correct_data():
    mock_session_local, mock_session = make_mock_session()
    with patch("app.repositories.projects.AsyncSessionLocal", mock_session_local):
        from app.repositories.projects import create_project
        metadata = {"title": "My Video", "duration": 120}
        result = await create_project(metadata)

    added_row = mock_session.add.call_args[0][0]
    assert added_row.project_id == result
    assert added_row.metadata_ == metadata


async def test_list_projects_empty():
    mock_session_local, mock_session = make_mock_session()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("app.repositories.projects.AsyncSessionLocal", mock_session_local):
        from app.repositories.projects import list_projects
        result = await list_projects()

    assert result == []


async def test_list_projects_returns_all_documents():
    now = datetime.now(timezone.utc)
    mock_row1 = MagicMock()
    mock_row1.project_id = "id-1"
    mock_row1.metadata_ = {"title": "A"}
    mock_row1.created_at = now
    mock_row1.updated_at = now

    mock_row2 = MagicMock()
    mock_row2.project_id = "id-2"
    mock_row2.metadata_ = {"title": "B"}
    mock_row2.created_at = now
    mock_row2.updated_at = now

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_row1, mock_row2]
    mock_session_local, mock_session = make_mock_session()
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("app.repositories.projects.AsyncSessionLocal", mock_session_local):
        from app.repositories.projects import list_projects
        result = await list_projects()

    assert len(result) == 2
    assert result[0]["project_id"] == "id-1"
    assert result[1]["project_id"] == "id-2"


async def test_list_projects_maps_fields_correctly():
    now = datetime.now(timezone.utc)
    mock_row = MagicMock()
    mock_row.project_id = "abc"
    mock_row.metadata_ = {"title": "Test"}
    mock_row.created_at = now
    mock_row.updated_at = now

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_row]
    mock_session_local, mock_session = make_mock_session()
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("app.repositories.projects.AsyncSessionLocal", mock_session_local):
        from app.repositories.projects import list_projects
        result = await list_projects()

    assert result[0]["metadata"] == {"title": "Test"}
    assert "id" not in result[0]


async def test_get_project_found():
    now = datetime.now(timezone.utc)
    mock_row = MagicMock()
    mock_row.project_id = "abc"
    mock_row.metadata_ = {"title": "T"}
    mock_row.created_at = now
    mock_row.updated_at = now

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_row
    mock_session_local, mock_session = make_mock_session()
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("app.repositories.projects.AsyncSessionLocal", mock_session_local):
        from app.repositories.projects import get_project
        result = await get_project("abc")

    assert result is not None
    assert result["project_id"] == "abc"


async def test_get_project_not_found():
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session_local, mock_session = make_mock_session()
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("app.repositories.projects.AsyncSessionLocal", mock_session_local):
        from app.repositories.projects import get_project
        result = await get_project("nonexistent")

    assert result is None


async def test_delete_project_found():
    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_session_local, mock_session = make_mock_session()
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("app.repositories.projects.AsyncSessionLocal", mock_session_local):
        from app.repositories.projects import delete_project
        result = await delete_project("abc")

    assert result is True


async def test_delete_project_not_found():
    mock_result = MagicMock()
    mock_result.rowcount = 0
    mock_session_local, mock_session = make_mock_session()
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("app.repositories.projects.AsyncSessionLocal", mock_session_local):
        from app.repositories.projects import delete_project
        result = await delete_project("nonexistent")

    assert result is False
