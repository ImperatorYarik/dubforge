import pytest
from unittest.mock import MagicMock, patch


def make_ydl_mock(info: dict) -> MagicMock:
    mock = MagicMock()
    mock.extract_info.return_value = info
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


async def test_returns_all_fields():
    info = {
        "title": "Test Video",
        "description": "A description",
        "thumbnail": "http://img.url/thumb.jpg",
        "duration": 120,
        "upload_date": "20260308",
        "uploader": "TestChannel",
    }
    with patch("app.utils.youtube_metadata.yt_dlp.YoutubeDL", return_value=make_ydl_mock(info)):
        from app.utils.youtube_metadata import get_youtube_metadata

        result = await get_youtube_metadata("https://youtube.com/watch?v=abc")

    assert result["title"] == "Test Video"
    assert result["description"] == "A description"
    assert result["thumbnail"] == "http://img.url/thumb.jpg"
    assert result["duration"] == 120
    assert result["upload_date"] == "20260308"
    assert result["uploader"] == "TestChannel"


async def test_missing_fields_return_none():
    with patch("app.utils.youtube_metadata.yt_dlp.YoutubeDL", return_value=make_ydl_mock({})):
        from app.utils.youtube_metadata import get_youtube_metadata

        result = await get_youtube_metadata("https://youtube.com/watch?v=abc")

    assert result["title"] is None
    assert result["description"] is None
    assert result["thumbnail"] is None
    assert result["duration"] is None
    assert result["upload_date"] is None
    assert result["uploader"] is None


async def test_extract_info_called_with_no_download():
    mock_ydl = make_ydl_mock({"title": "X"})
    with patch("app.utils.youtube_metadata.yt_dlp.YoutubeDL", return_value=mock_ydl):
        from app.utils.youtube_metadata import get_youtube_metadata

        await get_youtube_metadata("https://youtube.com/watch?v=abc")

    mock_ydl.extract_info.assert_called_once_with(
        "https://youtube.com/watch?v=abc", download=False
    )
