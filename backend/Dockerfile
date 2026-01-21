FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (keep minimal; wheels exist for most packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
  && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install -r /app/backend/requirements.txt

COPY backend /app/backend
COPY ragflow_config.json /app/ragflow_config.json

EXPOSE 8001

# Default config (override via env or compose)
ENV HOST=0.0.0.0 \
    PORT=8001 \
    DATABASE_PATH=data/auth.db \
    UPLOAD_DIR=data/uploads \
    PERMDBG_ENABLED=false

CMD ["python", "-m", "backend", "run", "--host", "0.0.0.0", "--port", "8001"]

