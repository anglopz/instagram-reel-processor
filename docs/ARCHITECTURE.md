# Architecture

## Clean Architecture Overview

The backend follows Clean Architecture with four concentric layers. Dependencies point inward — outer layers depend on inner layers, never the reverse.

```mermaid
graph TB
    subgraph Presentation["Presentation Layer"]
        Routes["FastAPI Routes"]
        Schemas["Pydantic Schemas"]
        Middleware["Error Handler"]
    end

    subgraph Application["Application Layer"]
        UseCases["Use Cases"]
        Ports["Port Interfaces (ABC)"]
        Services["Pipeline Orchestrator"]
    end

    subgraph Domain["Domain Layer"]
        Entities["Task, User"]
        Enums["TaskStatus"]
        Exceptions["DomainException hierarchy"]
    end

    subgraph Infrastructure["Infrastructure Layer"]
        Adapters["PostgresTaskRepository\nYtdlpDownloader\nFfmpegAudioExtractor\nWhisperTranscriber\nKeybertAnalyzer"]
        Celery["Celery Tasks + Callbacks"]
        Auth["JWT Handler, Password Hasher"]
        DB["SQLAlchemy Models, Session Factory"]
    end

    Routes --> UseCases
    Routes --> Schemas
    UseCases --> Ports
    UseCases --> Entities
    Adapters -.->|implements| Ports
    Celery --> Adapters
    Auth --> DB
    Services --> Celery
```

### Layer Rules

| Layer | May Import | Must Not Import |
|---|---|---|
| **Domain** | Python stdlib only | Application, Infrastructure, Presentation |
| **Application** | Domain | Infrastructure, Presentation |
| **Infrastructure** | Domain, Application | Presentation |
| **Presentation** | Domain, Application, Infrastructure* | — |

*Presentation imports infrastructure for DI wiring (`get_task_repository` dependency). The concrete adapter is resolved behind the abstract `TaskRepository` port interface.

## Dependency Injection

The DI container (`container.py`) is the single place where concrete adapters are wired to port interfaces:

```python
register_ports(
    task_repository=PostgresTaskRepository(session_factory),
    video_downloader=YtdlpDownloader(),
    audio_extractor=FfmpegAudioExtractor(),
    transcriber=WhisperTranscriber(),
    text_analyzer=KeybertAnalyzer(),
)
```

- **FastAPI routes** receive `TaskRepository` via `Depends(get_task_repository)`
- **Celery workers** resolve ports via a module-level registry, initialized on `worker_init` signal

## Processing Pipeline

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Redis
    participant Worker as Celery Worker
    participant DL as yt-dlp
    participant FF as FFmpeg
    participant WH as Whisper
    participant KB as KeyBERT

    Client->>API: POST /api/v1/tasks {reel_url}
    API->>DB: INSERT task (status=pending)
    API->>Redis: Dispatch Celery chain
    API-->>Client: 201 {task_id, status: pending}

    Worker->>Redis: Claim task
    Worker->>DB: SET status=processing

    Worker->>DL: Download video
    DL-->>Worker: /tmp/tasks/{id}/video.mp4

    Worker->>FF: Extract audio
    FF-->>Worker: /tmp/tasks/{id}/audio.wav

    Worker->>WH: Transcribe audio
    WH-->>Worker: {text, language}

    Worker->>KB: Extract topics
    KB-->>Worker: [topic1, topic2, ...]

    Worker->>DB: UPDATE transcript, language, topics
    Worker->>DB: SET status=completed
    Worker->>Worker: Cleanup /tmp/tasks/{id}/

    Client->>API: GET /api/v1/tasks/{id}
    API->>DB: SELECT task
    API-->>Client: {status: completed, language, topics}

    Client->>API: GET /api/v1/tasks/{id}/transcript
    API-->>Client: {transcript, language, topics}
```

### Cancellation Flow

1. Client sends `POST /api/v1/tasks/{id}/cancel`
2. API sets task status to `CANCELLED` in PostgreSQL
3. Each pipeline step checks status before executing via an atomic `UPDATE...WHERE status NOT IN (terminal_states)`
4. If the task is cancelled, the step returns early and the chain aborts
5. In-progress steps complete before the check — cancellation is cooperative, not preemptive

## Database Schema

```mermaid
erDiagram
    users {
        uuid id PK
        varchar email UK
        varchar hashed_password
        timestamp created_at
    }

    tasks {
        uuid id PK
        uuid user_id FK
        text reel_url
        varchar status
        varchar celery_task_id
        text transcript
        varchar language
        jsonb topics
        text error_message
        timestamp created_at
        timestamp updated_at
    }

    users ||--o{ tasks : "has many"
```

**Indexes:** `idx_tasks_user_id`, `idx_tasks_status`

## Auth Flow

1. **Register:** `POST /auth/register` → hash password with bcrypt → store user → return JWT
2. **Login:** `POST /auth/login` → verify password → return JWT
3. **Protected routes:** `Authorization: Bearer <token>` → `HTTPBearer` extracts token → `verify_token` decodes JWT → extract `user_id` from `sub` claim
4. **Token expiration:** Configurable via `JWT_EXPIRATION_MINUTES` (default: 60 min)

## Error Handling

Errors propagate from adapters through domain exceptions to HTTP responses:

```
Adapter raises exception
  → Celery task catches it
    → callbacks.handle_failure() sets task status to FAILED
    → Error message stored in task.error_message

Domain exception raised in use case
  → FastAPI exception handler catches DomainException
    → Returns JSON: {detail, error_code} with appropriate HTTP status

Unhandled exception
  → Generic exception handler catches Exception
    → Returns 500: {detail: "Internal server error"}
    → Full traceback logged server-side
```

| Exception | HTTP Status | Error Code |
|---|---|---|
| `TaskNotFound` | 404 | `TASK_NOT_FOUND` |
| `InvalidURL` | 422 | `INVALID_URL` |
| `Unauthorized` | 401 | `UNAUTHORIZED` |
| `TaskAlreadyTerminal` | 409 | `TASK_ALREADY_TERMINAL` |
| `PipelineError` | 500 | `PIPELINE_ERROR` |

## Concurrency

- **Celery workers** process tasks with `concurrency=2` (prefork pool)
- **Each task** is a chain of 5 sequential steps — parallelism is across tasks, not within a task
- **Async I/O** in adapters uses `asyncio.to_thread()` for blocking operations (FFmpeg, Whisper)
- **Celery tasks** bridge async ports via `asyncio.run()`, creating a fresh event loop per step
- **Database connections** use SQLAlchemy's async session factory with connection pooling

## Testing Strategy

- **Unit tests** — Domain entities, use cases, and adapters tested in isolation with mocked ports
- **Integration tests** — Repository tests against SQLite with JSONB→JSON type remapping
- **Pytest-asyncio** for async test functions with `asyncio_mode = "auto"`
