FROM python:3.11-slim

WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY packages ./packages
COPY apps ./apps
RUN pip install --upgrade pip && pip install ".[ui]"

EXPOSE 8501
CMD ["streamlit", "run", "apps/ui/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
