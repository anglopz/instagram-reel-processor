# Architecture Decision Records

## ADR-001: FastAPI over Django

**Status:** Accepted

**Context:** The project needs a Python web framework for a REST API that handles async task dispatch, JWT authentication, and auto-generated API documentation. Django and FastAPI are the two leading choices.

**Decision:** Use FastAPI with Pydantic for request/response validation.

**Rationale:** FastAPI is async-native (built on Starlette + uvicorn), which aligns naturally with the async SQLAlchemy sessions and Celery dispatch. It generates OpenAPI/Swagger docs automatically from Pydantic schemas, reducing documentation overhead. Django's ORM is synchronous by default, and Django REST Framework adds significant boilerplate for what is a relatively simple API surface (7 endpoints).

**Alternatives considered:**
- **Django + DRF:** More batteries-included (admin panel, migrations built-in), but the sync ORM would require `sync_to_async` wrappers everywhere. DRF serializers duplicate what Pydantic already does. Overkill for 7 endpoints.
- **Flask:** Lightweight but lacks built-in validation, async support, and auto-docs. Would require Flask-RESTful + Marshmallow + flask-cors, approaching DRF's boilerplate.

**Consequences:**
- (+) Native async, zero-boilerplate validation, auto-generated docs
- (+) Pydantic schemas serve as both validation and documentation
- (-) No built-in admin panel (not needed for this project)
- (-) Alembic must be configured manually (vs. Django's built-in migrations)

---

## ADR-002: Celery over FastAPI BackgroundTasks

**Status:** Accepted

**Context:** The processing pipeline (download → extract → transcribe → analyze → persist) takes 30 seconds to several minutes. It needs to run asynchronously with status tracking, retry logic, and cancellation support.

**Decision:** Use Celery with Redis as broker, implementing the pipeline as a chain of 5 tasks.

**Rationale:** FastAPI's `BackgroundTasks` runs in the same process as the API server — a long-running transcription would block the worker thread pool. Celery provides: (1) separate worker processes that can be scaled independently, (2) `chain()` primitive for sequential pipeline steps, (3) automatic retries with configurable delays, (4) task state tracking, and (5) `revoke()` for cancellation. The pipeline's step-by-step nature maps naturally to Celery's chain primitive.

**Alternatives considered:**
- **FastAPI BackgroundTasks:** Simplest option, zero infrastructure. But no retries, no cancellation, no independent scaling, and a crashed task takes down the API process.
- **Dramatiq:** Cleaner API than Celery, but smaller ecosystem, less documentation, and no native chain primitive.
- **AWS Step Functions / Temporal:** Production-grade orchestration but requires cloud infrastructure or a separate Temporal server. Overkill for a take-home challenge.

**Consequences:**
- (+) Independent worker scaling, retries, chain primitives, cancellation
- (+) Redis serves double duty as broker and result backend
- (-) Adds operational complexity (separate worker process, Redis dependency)
- (-) Celery's module-level task registration complicates dependency injection (solved via port registry pattern)

---

## ADR-003: Local Whisper over Cloud Speech-to-Text

**Status:** Accepted

**Context:** The pipeline needs speech-to-text transcription with language detection. Options are cloud APIs (Google STT, AWS Transcribe, AssemblyAI) or local inference with OpenAI's Whisper model.

**Decision:** Use OpenAI Whisper running locally in the Celery worker.

**Rationale:** Local Whisper eliminates API key management, network latency, and per-request costs. It supports 99 languages with automatic detection. For a code challenge, self-contained infrastructure (no external API dependencies) makes the project easier to evaluate — reviewers can `docker compose up` without configuring third-party credentials. The `base` model (140 MB) offers a good accuracy/speed tradeoff for demonstration purposes.

**Alternatives considered:**
- **Google Cloud STT:** Higher accuracy for production, but requires a GCP project, service account, and billing. Evaluators would need their own credentials.
- **AssemblyAI:** Excellent developer experience, but same credential problem.
- **Faster-Whisper (CTranslate2):** 4x faster than OpenAI Whisper with lower memory usage. Would be the production choice, but adds a C++ dependency that complicates the Docker build.

**Consequences:**
- (+) Zero external dependencies — fully self-contained in Docker
- (+) Automatic language detection included
- (+) No API keys, no network calls, no usage costs
- (-) First run downloads the model (~140 MB)
- (-) CPU inference is slower than cloud APIs (mitigated by Celery's async processing)
- (-) GPU acceleration requires CUDA setup in Docker (not included)

---

## ADR-004: POST for Cancel (not DELETE or PATCH)

**Status:** Accepted

**Context:** The cancel endpoint needs to transition a task from PENDING/PROCESSING to CANCELLED. The HTTP method choice affects the API's REST semantics.

**Decision:** Use `POST /tasks/{id}/cancel` as an action endpoint.

**Rationale:** Cancellation is a state transition (an action), not a resource deletion or partial update. `DELETE /tasks/{id}` implies the resource is removed, but cancelled tasks remain in the database with their metadata intact. `PATCH /tasks/{id}` with `{status: "cancelled"}` would work semantically but opens the door to arbitrary status changes — the client shouldn't be able to set a task to "completed" via PATCH. A dedicated `POST /cancel` endpoint makes the intent explicit and limits the action to exactly one state transition.

**Alternatives considered:**
- **DELETE /tasks/{id}:** Misleading — the task is not deleted, just cancelled. Would conflict with an actual delete endpoint if added later.
- **PATCH /tasks/{id}:** Overly generic — would need server-side validation to restrict which status transitions are allowed. More surface area for bugs.
- **PUT /tasks/{id}/status:** RESTful but awkward — treating "status" as a sub-resource feels forced.

**Consequences:**
- (+) Intent is unambiguous — the endpoint does exactly one thing
- (+) No risk of unintended state transitions
- (-) Not strictly RESTful (purists prefer resource-oriented verbs)
- (-) Adds a sub-route rather than using standard HTTP methods on the resource

---

## ADR-005: Clean Architecture for a Take-Home Challenge

**Status:** Accepted

**Context:** Take-home challenges are evaluated on code quality, design decisions, and engineering maturity. The question is whether Clean Architecture (4 layers, ports/adapters, dependency inversion) is justified for a project of this size, or whether it's over-engineering.

**Decision:** Use Clean Architecture with explicit layers, port interfaces, and dependency injection.

**Rationale:** The primary audience is code challenge reviewers evaluating architectural thinking. Clean Architecture demonstrates: (1) understanding of dependency inversion and interface segregation, (2) ability to design testable code with swappable implementations, (3) clear separation between business logic and infrastructure concerns. The pipeline's 5 external dependencies (yt-dlp, FFmpeg, Whisper, KeyBERT, PostgreSQL) are ideal candidates for port/adapter abstraction — each can be tested with a mock without spinning up the real service.

**Alternatives considered:**
- **Simple layered architecture (routes → services → models):** Faster to build, less boilerplate. But misses the opportunity to demonstrate dependency inversion, and testing requires real infrastructure or complex mocking.
- **No architecture (everything in route handlers):** Fastest to build, but gives reviewers nothing to discuss in the technical interview.

**Consequences:**
- (+) Every external dependency is behind an abstract port — fully testable with mocks
- (+) Demonstrates SOLID principles in practice, not just theory
- (+) Clear interview talking points: "here's why I chose this boundary," "here's the trade-off"
- (-) More files and indirection than strictly necessary for 7 endpoints
- (-) Some pragmatic violations remain (auth routes bypass ports for simplicity — a deliberate trade-off documented here)
