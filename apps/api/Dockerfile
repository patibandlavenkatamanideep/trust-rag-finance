FROM python:3.11-slim

WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# Copy the monorepo and install it (pulls packages/* via pyproject find).
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY apps ./apps
RUN pip install --upgrade pip && pip install .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
