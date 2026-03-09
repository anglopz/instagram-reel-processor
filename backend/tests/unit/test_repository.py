from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import JSON, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.domain.entities.task import Task
from src.domain.enums.task_status import TaskStatus
from src.infrastructure.adapters.postgres_task_repository import PostgresTaskRepository
from src.infrastructure.database.models import Base, TaskModel, UserModel


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
async def engine():
    """In-memory SQLite async engine for testing.

    Remaps PostgreSQL JSONB → generic JSON so SQLite can handle it.
    """
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")

    # SQLite doesn't enforce FKs by default — enable them
    @event.listens_for(eng.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Remap JSONB → JSON for SQLite compatibility
    @event.listens_for(eng.sync_engine, "connect")
    def _remap_jsonb(dbapi_conn, _record):
        pass  # pragma: no cover

    # Patch JSONB columns to JSON before creating tables
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, JSONB):
                col.type = JSON()

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def session(session_factory):
    async with session_factory() as s:
        yield s


@pytest.fixture
async def user_id(session):
    """Insert a test user and return their UUID."""
    uid = uuid4()
    user = UserModel(
        id=uid,
        email="test@example.com",
        hashed_password="hashed",
    )
    session.add(user)
    await session.commit()
    return uid


@pytest.fixture
async def other_user_id(session):
    """Insert a second test user."""
    uid = uuid4()
    user = UserModel(
        id=uid,
        email="other@example.com",
        hashed_password="hashed",
    )
    session.add(user)
    await session.commit()
    return uid


@pytest.fixture
def repo(session_factory):
    return PostgresTaskRepository(session_factory)


def _make_task(user_id, **overrides):
    defaults = dict(
        id=uuid4(),
        reel_url="https://www.instagram.com/reel/abc123/",
        status=TaskStatus.PENDING,
        user_id=user_id,
    )
    defaults.update(overrides)
    return Task(**defaults)


# ── Create ──────────────────────────────────────────────────────────────


class TestCreate:
    async def test_create_returns_task(self, repo, user_id):
        task = _make_task(user_id)
        result = await repo.create(task)
        assert result.id == task.id
        assert result.reel_url == task.reel_url
        assert result.status == TaskStatus.PENDING
        assert result.user_id == user_id

    async def test_create_persists_to_db(self, repo, user_id):
        task = _make_task(user_id)
        await repo.create(task)
        fetched = await repo.get_by_id(task.id, user_id)
        assert fetched is not None
        assert fetched.id == task.id


# ── Get by ID ───────────────────────────────────────────────────────────


class TestGetById:
    async def test_returns_task_for_owner(self, repo, user_id):
        task = _make_task(user_id)
        await repo.create(task)
        result = await repo.get_by_id(task.id, user_id)
        assert result is not None
        assert result.id == task.id

    async def test_returns_none_for_wrong_user(self, repo, user_id, other_user_id):
        """Task exists but belongs to user_id — other_user_id should get None (→ 404)."""
        task = _make_task(user_id)
        await repo.create(task)
        result = await repo.get_by_id(task.id, other_user_id)
        assert result is None

    async def test_returns_none_for_nonexistent_task(self, repo, user_id):
        result = await repo.get_by_id(uuid4(), user_id)
        assert result is None


# ── Get by user ID (list) ───────────────────────────────────────────────


class TestGetByUserId:
    async def test_returns_only_own_tasks(self, repo, user_id, other_user_id):
        t1 = _make_task(user_id)
        t2 = _make_task(other_user_id)
        await repo.create(t1)
        await repo.create(t2)

        results = await repo.get_by_user_id(user_id)
        assert len(results) == 1
        assert results[0].id == t1.id

    async def test_pagination_limit(self, repo, user_id):
        for _ in range(5):
            await repo.create(_make_task(user_id))
        results = await repo.get_by_user_id(user_id, limit=3)
        assert len(results) == 3

    async def test_pagination_offset(self, repo, user_id):
        for _ in range(5):
            await repo.create(_make_task(user_id))
        all_tasks = await repo.get_by_user_id(user_id, limit=100)
        offset_tasks = await repo.get_by_user_id(user_id, limit=100, offset=2)
        assert len(offset_tasks) == 3
        assert offset_tasks[0].id == all_tasks[2].id

    async def test_empty_list_for_user_with_no_tasks(self, repo, user_id):
        results = await repo.get_by_user_id(user_id)
        assert results == []


# ── Update status ───────────────────────────────────────────────────────


class TestUpdateStatus:
    async def test_updates_status(self, repo, user_id):
        task = _make_task(user_id)
        await repo.create(task)
        result = await repo.update_status(task.id, TaskStatus.PROCESSING)
        assert result is not None
        assert result.status == TaskStatus.PROCESSING

    async def test_updates_status_with_error_message(self, repo, user_id):
        task = _make_task(user_id)
        await repo.create(task)
        result = await repo.update_status(
            task.id, TaskStatus.FAILED, error_message="download failed"
        )
        assert result is not None
        assert result.status == TaskStatus.FAILED
        assert result.error_message == "download failed"

    async def test_returns_none_for_nonexistent_task(self, repo, user_id):
        result = await repo.update_status(uuid4(), TaskStatus.PROCESSING)
        assert result is None


# ── Update results ──────────────────────────────────────────────────────


class TestUpdateResults:
    async def test_updates_transcript_language_topics(self, repo, user_id):
        task = _make_task(user_id)
        await repo.create(task)
        result = await repo.update_results(
            task.id,
            transcript="Hello world",
            language="en",
            topics=["greeting", "world"],
        )
        assert result is not None
        assert result.transcript == "Hello world"
        assert result.language == "en"
        assert result.topics == ["greeting", "world"]

    async def test_returns_none_for_nonexistent_task(self, repo, user_id):
        result = await repo.update_results(
            uuid4(), transcript="text", language="en", topics=[]
        )
        assert result is None
