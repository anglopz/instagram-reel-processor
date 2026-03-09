# How To Run

## Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Start PostgreSQL and Redis (or use Docker)
# Set DATABASE_URL and REDIS_URL in .env

alembic upgrade head
uvicorn src.main:app --reload --port 8000

# In a separate terminal:
celery -A src.infrastructure.celery.app:celery_app worker --loglevel=info
```

## Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173, proxies /api to localhost:8000
```

## Docker (recommended)

```bash
cp .env.example .env
docker compose up --build
# API: http://localhost:8000/docs
# Frontend: http://localhost:5173
```

## Processing Pipeline

1. User submits an Instagram Reel URL via the frontend or `POST /api/v1/tasks`
2. The API creates a task record (status: `pending`) and dispatches a Celery chain
3. The Celery worker executes 5 sequential steps:
   - **Download** — yt-dlp fetches the video from Instagram
   - **Extract audio** — FFmpeg converts video to 16kHz mono WAV
   - **Transcribe** — OpenAI Whisper converts speech to text and detects language
   - **Analyze** — KeyBERT extracts topic keywords from the transcript
   - **Persist** — Results are saved to PostgreSQL, status set to `completed`
4. The frontend polls `GET /api/v1/tasks` every 3 seconds to display progress
5. Users can cancel pending/processing tasks, which aborts the pipeline at the next step boundary
