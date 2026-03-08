from fastapi import FastAPI
from app.routers import videos
from app.routers import projects
from app.utils.storage import storage
from app.config import settings

app = FastAPI()

#Initialize storage
storage.create_bucket(settings.BUCKET_NAME)


app.include_router(projects.router, prefix="/projects", tags=["projects"])

app.include_router(videos.router, prefix="/videos", tags=["videos"])

