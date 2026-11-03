from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AgentSpec:
    id: str
    name: str
    role: str
    description: str
    capabilities: tuple[str, ...]
    risk_level: str = "low"
    status: str = "ready"


@dataclass
class Task:
    prompt: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "queued"
    route: str = "vision-core"
    risk: str = "low"
    result: str = ""
    error: str = ""
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    subtasks: list[dict[str, Any]] = field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = utc_now()
