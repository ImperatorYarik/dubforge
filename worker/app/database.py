from pymongo import MongoClient
from app.config import settings

client = MongoClient(settings.MONGO_URI)

db = client['video_db']

projects_collection = db["projects"]
videos_collection = db["videos"]




