FROM python:3.11-slim

WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# Copy the monorepo and install it (pulls packages/* via pyproject find).
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY apps ./apps
COPY data ./data
RUN pip install --upgrade pip && pip install .

EXPOSE 8000
# Honor Railway's injected $PORT (falls back to 8000 locally). Shell form so the
# env var is expanded at runtime.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
