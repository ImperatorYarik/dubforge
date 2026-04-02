# syntax=docker/dockerfile:1
# Lightweight app image — only copies source code on top of the pre-built base.
# Build the base first (one-time, ~500s):
#   docker build -f worker/Dockerfile.base -t video-trans-worker-base worker/
# Subsequent builds are instant (~5s):
#   docker compose up --build worker
FROM video-trans-worker-base:latest

WORKDIR /app
COPY app/ ./app/

CMD ["celery", "-A", "app.celery_app.celery", "worker", "--loglevel=info"]
