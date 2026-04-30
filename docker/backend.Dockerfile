FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install backend package
COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/app /app/backend/app
RUN pip install -e /app/backend

# Strava export is mounted read-only at /export by compose.
# Generated DB + Parquet live in /app/data (mounted volume).
ENV CV_DATA_DIR=/app/data \
    CV_REPO_ROOT=/app

EXPOSE 8000
WORKDIR /app/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
