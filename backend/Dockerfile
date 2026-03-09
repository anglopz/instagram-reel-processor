FROM python:3.11-slim

# Install system deps (ffmpeg for audio extraction)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

# Run as non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Default command — overridden by docker-compose for worker
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
