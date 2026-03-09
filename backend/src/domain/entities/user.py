from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


@dataclass
class User:
    id: UUID
    email: str
    hashed_password: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
