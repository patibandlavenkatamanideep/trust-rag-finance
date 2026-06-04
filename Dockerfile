# Combined image for Railway: one container runs the FastAPI backend (internal
# :8000) and the Streamlit UI (public $PORT). See scripts/start.sh.
FROM python:3.11-slim

WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# Install the monorepo + the UI extra (FastAPI, retrieval, Streamlit, ...).
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY apps ./apps
COPY data ./data
COPY scripts ./scripts
RUN pip install --upgrade pip && pip install ".[ui]"

# Public port is Streamlit; Railway injects $PORT at runtime.
EXPOSE 8501
CMD ["bash", "scripts/start.sh"]
