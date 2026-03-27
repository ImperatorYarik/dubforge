from celery import Celery
from celery.signals import worker_process_init
from app.config import settings

celery = Celery(
    'video_trans_worker',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.pipelines.dubbing_pipeline",
        "app.pipelines.transcribe_pipeline",
        "app.pipelines.tts_pipeline",
        "app.pipelines.demucs_pipeline",
        "app.tasks.collect_context",
        "app.tasks.translate_segments",
    ],
)

celery.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    worker_pool='solo',
)


@worker_process_init.connect
def init_model(**kwargs):
    from app.services.model_manager import model_manager
    model_manager.get_whisper()
