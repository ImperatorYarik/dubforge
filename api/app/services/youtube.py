import yt_dlp
from fastapi.concurrency import run_in_threadpool


async def get_youtube_metadata(url: str) -> dict:
    def _fetch():
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title"),
                "description": info.get("description"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "upload_date": info.get("upload_date"),
                "uploader": info.get("uploader"),
            }

    return await run_in_threadpool(_fetch)


async def download_youtube_video(url: str, output_path: str) -> bool:
    def _download():
        try:
            ydl_opts = {
                "quiet": True,
                "outtmpl": output_path,
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            print(f"Error downloading video: {e}")
            return False

    return await run_in_threadpool(_download)
