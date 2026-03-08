import yt_dlp
from fastapi.concurrency import run_in_threadpool


async def get_youtube_metadata(url: str) -> dict:
    def _fetch():
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            metadata = ydl.extract_info(url, download=False)
            return {
                "title": metadata.get("title"),
                "description": metadata.get("description"),
                "thumbnail": metadata.get("thumbnail"),
                "duration": metadata.get("duration"),
                "upload_date": metadata.get("upload_date"),
                "uploader": metadata.get("uploader"),
            }
    
    return await run_in_threadpool(_fetch)