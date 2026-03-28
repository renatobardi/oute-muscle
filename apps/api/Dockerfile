# T174: FastAPI API Dockerfile — multi-stage build
#
# Stage 1: builder   — installs Python deps into a virtual env
# Stage 2: runtime   — copies the venv + source, runs as non-root
#
# Build args:
#   PYTHON_VERSION  (default 3.12)
#   APP_PORT        (default 8000)

ARG PYTHON_VERSION=3.12

# ─────────────────────────────────────────────────────────────
# Stage 1 – builder
# ─────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS builder

WORKDIR /build

# System deps for psycopg2-binary / semgrep
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pip-tools for deterministic installs
RUN pip install --no-cache-dir pip==24.* uv==0.4.*

# Copy dependency manifests first (layer-cache friendly)
COPY apps/api/requirements.txt           apps/api/requirements.txt
COPY packages/core/requirements.txt      packages/core/requirements.txt
COPY packages/db/requirements.txt        packages/db/requirements.txt

# Create virtualenv and install all deps
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir \
    -r apps/api/requirements.txt \
    -r packages/core/requirements.txt \
    -r packages/db/requirements.txt

# Copy source
COPY apps/api/      apps/api/
COPY packages/core/ packages/core/
COPY packages/db/   packages/db/

# Install local packages so they are importable as Python modules
RUN pip install --no-cache-dir --no-deps \
    -e packages/core \
    -e packages/db \
    -e apps/api

# ─────────────────────────────────────────────────────────────
# Stage 2 – runtime
# ─────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS runtime

ARG APP_PORT=8000
ENV APP_PORT=${APP_PORT} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Runtime system deps (libpq for asyncpg, semgrep binary dep)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd --gid 1001 appgroup && \
    useradd  --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application source
COPY --from=builder /build/apps/api/      apps/api/
COPY --from=builder /build/packages/core/ packages/core/
COPY --from=builder /build/packages/db/   packages/db/

# Ensure the app user owns the working directory
RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE ${APP_PORT}

# Uvicorn: 1 worker per CPU core, managed by Cloud Run autoscaling
CMD ["sh", "-c", "uvicorn apps.api.src.main:app \
    --host 0.0.0.0 \
    --port ${APP_PORT} \
    --workers 1 \
    --loop uvloop \
    --no-access-log"]
