import os
import shutil
import logging
from celery import Task

from app.services.model_manager import model_manager

logger = logging.getLogger(__name__)


class BasePipeline(Task):
    abstract = True

    def _make_tmp(self, name: str) -> str:
        path = f"/tmp/{name}"  # nosec B108 — intentional, worker runs in an isolated container
        os.makedirs(path, exist_ok=True)
        return path

    def _cleanup_tmp(self, name: str) -> None:
        shutil.rmtree(f"/tmp/{name}", ignore_errors=True)  # nosec B108

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        model_manager.release_all()
