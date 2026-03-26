import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.storage import storage
from app.routers import jobs, projects, system, tts, videos

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions so they pass through CORSMiddleware."""
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# Initialize storage bucket on startup
storage.create_bucket(settings.BUCKET_NAME)

app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(videos.router, prefix="/videos", tags=["videos"])
app.include_router(tts.router, prefix="/tts", tags=["tts"])
app.include_router(system.router, prefix="/system", tags=["system"])
