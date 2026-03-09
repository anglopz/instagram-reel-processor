# Instagram Reel Processor

A fullstack application that processes Instagram Reels through an async pipeline: downloading videos, extracting audio, transcribing speech with OpenAI Whisper, detecting language, and extracting topics with KeyBERT. Built with Clean Architecture, FastAPI, Celery, React, and Docker Compose.

## Architecture

```mermaid
graph LR
    Client[React Frontend] -->|REST API| API[FastAPI]
    API -->|Dispatch chain| Redis[(Redis)]
    Redis -->|Consume tasks| Worker[Celery Worker]
    API -->|Read/Write| PG[(PostgreSQL)]
    Worker -->|Update status| PG
    Worker -->|Download| FFmpeg[yt-dlp + FFmpeg]
    Worker -->|Transcribe| Whisper[OpenAI Whisper]
    Worker -->|Analyze| KeyBERT[KeyBERT]
```

## Tech Stack

| Technology | Version | Why |
|---|---|---|
| **FastAPI** | 0.115+ | Async-native, auto-generated OpenAPI docs, Pydantic validation |
| **Celery** | 5.4+ | Distributed task queue with chain primitives, retries, and cancellation |
| **PostgreSQL** | 16 | JSONB for topics, UUID PKs, robust ACID transactions |
| **Redis** | 7 | Celery broker and result backend — fast, lightweight |
| **SQLAlchemy** | 2.0+ | Async ORM with `asyncpg` driver, declarative models |
| **OpenAI Whisper** | latest | Local speech-to-text — no API keys, supports 99 languages |
| **KeyBERT** | 0.8+ | Keyword extraction via sentence embeddings — lightweight |
| **React** | 18 | Component-based UI with hooks, context API for auth |
| **Vite** | 6 | Sub-second HMR, built-in proxy for API calls |
| **Tailwind CSS** | 4 | Utility-first styling with Vite plugin |
| **Docker Compose** | — | Single-command orchestration of all 5 services |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

## Quick Start

```bash
# Clone and start
git clone <repo-url> && cd instagram-reel-processor
cp .env.example .env
docker compose up --build
```

> **Note:** On first run, Whisper downloads the model (~140 MB for `base`). This happens once and is cached in the container volume.

- **API docs:** http://localhost:8000/docs
- **Frontend:** http://localhost:5173

## API Endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Register a new user | No |
| `POST` | `/api/v1/auth/login` | Login and get JWT token | No |
| `GET` | `/api/v1/tasks` | List current user's tasks | Yes |
| `POST` | `/api/v1/tasks` | Create a processing task | Yes |
| `GET` | `/api/v1/tasks/{id}` | Get task status and metadata | Yes |
| `GET` | `/api/v1/tasks/{id}/transcript` | Get transcript, language, topics | Yes |
| `POST` | `/api/v1/tasks/{id}/cancel` | Cancel a pending/processing task | Yes |
| `GET` | `/api/v1/health` | Health check | No |

## Processing Pipeline

When a task is created via `POST /api/v1/tasks`:

1. **Download** — `yt-dlp` downloads the Instagram Reel video to a temp directory
2. **Extract Audio** — `FFmpeg` extracts audio as 16kHz mono WAV (optimized for Whisper)
3. **Transcribe** — OpenAI Whisper transcribes audio and detects language
4. **Analyze** — KeyBERT extracts topic keywords from the transcript
5. **Persist** — Results (transcript, language, topics) are saved to PostgreSQL

Each step checks for cancellation before executing. Failed steps trigger automatic retries (download: 3x, transcribe: 2x). Temp files are cleaned up on both success and failure.

## Project Structure

```
instagram-reel-processor/
├── backend/
│   ├── src/
│   │   ├── domain/              # Entities, enums, exceptions (zero deps)
│   │   ├── application/         # Ports (interfaces), use cases, services
│   │   ├── infrastructure/      # Adapters, database, Celery, auth
│   │   ├── presentation/        # FastAPI routes, schemas, middleware
│   │   ├── container.py         # DI wiring — ports to concrete adapters
│   │   └── main.py              # FastAPI app factory
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Unit and integration tests
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/          # TaskList, TaskCard, AddTaskModal, etc.
│   │   ├── pages/               # Login, Register, Dashboard
│   │   ├── context/             # AuthContext (JWT management)
│   │   └── services/            # Axios API client
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml           # PostgreSQL + Redis + API + Worker + Frontend
├── .env.example
└── docs/
    ├── ARCHITECTURE.md
    └── DECISIONS.md
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://app:changeme@postgres:5432/reel_processor` | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection for Celery |
| `SECRET_KEY` | `change-this-...` | JWT signing key (**change in production**) |
| `WHISPER_MODEL` | `base` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large` |
| `POSTGRES_USER` | `app` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `changeme` | PostgreSQL password (**change in production**) |
| `POSTGRES_DB` | `reel_processor` | PostgreSQL database name |

## Known Limitations

- **Instagram rate limiting** — yt-dlp may be blocked by Instagram after repeated downloads; no proxy rotation implemented
- **Whisper model size vs. accuracy** — `base` model is fast but less accurate than `large`; configurable via `WHISPER_MODEL`
- **No horizontal worker scaling** — Single Celery worker with `concurrency=2`; production would use multiple workers
- **Development-only frontend** — Vite dev server used in Docker; production would use nginx serving a static build
- **No persistent file storage** — Processed media is stored in `/tmp` and deleted after pipeline completion
