from celery import Celery
from app.config import settings

celery = Celery(broker=settings.REDIS_URL)