from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client = AsyncIOMotorClient(settings.MONGO_URI)

db = client["video_db"]

projects_collection = db["projects"]
videos_collection = db["videos"]
