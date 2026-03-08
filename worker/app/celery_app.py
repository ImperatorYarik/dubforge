from celery import Celery
from celery.signals import worker_process_init
from app.config import settings

celery = Celery(
    'video_trans_worker',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.pipeline"],
)

celery.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    worker_pool='solo',  # no forking — required for CUDA
)


@worker_process_init.connect
def init_model(**kwargs):
    """Pre-load the Whisper model when the worker process starts."""
    from worker.app.tasks.translate import get_model
    get_model()