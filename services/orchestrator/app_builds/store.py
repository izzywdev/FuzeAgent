"""Durable session store. ``update`` is an atomic read-modify-write (row lock in Postgres)."""

from __future__ import annotations

import asyncio
import copy
import json
from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional, Tuple, TypeVar

from .models import TERMINAL, BuildRecord

T = TypeVar("T")


class BuildStore(ABC):
    @abstractmethod
    async def create_if_absent(self, rec: BuildRecord) -> Tuple[BuildRecord, bool]:
        """Insert unless ``build_session_id`` exists. Returns (stored_record, created)."""

    @abstractmethod
    async def get(self, build_session_id: str) -> Optional[BuildRecord]: ...

    @abstractmethod
    async def update(
        self, build_session_id: str, mutator: Callable[[BuildRecord], T]
    ) -> Optional[T]:
        """Atomically apply ``mutator`` to the record; None if the record does not exist."""

    @abstractmethod
    async def list_active(self) -> List[BuildRecord]:
        """Non-terminal sessions (to resume after a restart)."""

    @abstractmethod
    async def list_pending_outbox(self) -> List[BuildRecord]:
        """Sessions with at least one pending callback."""


class InMemoryBuildStore(BuildStore):
    def __init__(self) -> None:
        self._rows: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def create_if_absent(self, rec: BuildRecord) -> Tuple[BuildRecord, bool]:
        async with self._lock:
            existing = self._rows.get(rec.build_session_id)
            if existing is not None:
                return BuildRecord.from_dict(copy.deepcopy(existing)), False
            self._rows[rec.build_session_id] = copy.deepcopy(rec.to_dict())
            return rec, True

    async def get(self, build_session_id: str) -> Optional[BuildRecord]:
        async with self._lock:
            row = self._rows.get(build_session_id)
            return BuildRecord.from_dict(copy.deepcopy(row)) if row else None

    async def update(
        self, build_session_id: str, mutator: Callable[[BuildRecord], T]
    ) -> Optional[T]:
        async with self._lock:
            row = self._rows.get(build_session_id)
            if row is None:
                return None
            rec = BuildRecord.from_dict(copy.deepcopy(row))
            result = mutator(rec)
            self._rows[build_session_id] = copy.deepcopy(rec.to_dict())
            return result

    async def list_active(self) -> List[BuildRecord]:
        async with self._lock:
            return [
                BuildRecord.from_dict(copy.deepcopy(r))
                for r in self._rows.values()
                if r["status"] not in TERMINAL
            ]

    async def list_pending_outbox(self) -> List[BuildRecord]:
        async with self._lock:
            return [
                BuildRecord.from_dict(copy.deepcopy(r))
                for r in self._rows.values()
                if any(e["state"] == "pending" for e in r["outbox"])
            ]


class PostgresBuildStore(BuildStore):
    """``app_build_sessions`` (migration 20261004_120001). ``connect`` yields an asyncpg
    connection as an async context manager (``database.get_db_connection``); the jsonb codec it
    registers lets us pass/receive plain dicts."""

    def __init__(self, connect: Callable[[], Any]) -> None:
        self._connect = connect

    @staticmethod
    def _row_fields(rec: BuildRecord) -> tuple:
        return (rec.status, rec.has_pending_outbox(), rec.to_dict())

    async def create_if_absent(self, rec: BuildRecord) -> Tuple[BuildRecord, bool]:
        status, pending, data = self._row_fields(rec)
        async with self._connect() as conn:
            row = await conn.fetchrow(
                """INSERT INTO app_build_sessions
                       (build_session_id, agent_session_ref, status, has_pending_outbox, data)
                   VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (build_session_id) DO NOTHING
                   RETURNING data""",
                rec.build_session_id,
                rec.agent_session_ref,
                status,
                pending,
                data,
            )
            if row is not None:
                return rec, True
            existing = await conn.fetchrow(
                "SELECT data FROM app_build_sessions WHERE build_session_id = $1",
                rec.build_session_id,
            )
            return BuildRecord.from_dict(_as_dict(existing["data"])), False

    async def get(self, build_session_id: str) -> Optional[BuildRecord]:
        async with self._connect() as conn:
            row = await conn.fetchrow(
                "SELECT data FROM app_build_sessions WHERE build_session_id = $1",
                build_session_id,
            )
        return BuildRecord.from_dict(_as_dict(row["data"])) if row else None

    async def update(
        self, build_session_id: str, mutator: Callable[[BuildRecord], T]
    ) -> Optional[T]:
        async with self._connect() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT data FROM app_build_sessions WHERE build_session_id = $1 FOR UPDATE",
                    build_session_id,
                )
                if row is None:
                    return None
                rec = BuildRecord.from_dict(_as_dict(row["data"]))
                result = mutator(rec)
                status, pending, data = self._row_fields(rec)
                await conn.execute(
                    """UPDATE app_build_sessions
                          SET status = $2, has_pending_outbox = $3, data = $4, updated_at = now()
                        WHERE build_session_id = $1""",
                    build_session_id,
                    status,
                    pending,
                    data,
                )
                return result

    async def list_active(self) -> List[BuildRecord]:
        async with self._connect() as conn:
            rows = await conn.fetch(
                "SELECT data FROM app_build_sessions WHERE status NOT IN ('deployed','failed','cancelled') "
                "ORDER BY created_at LIMIT 500"
            )
        return [BuildRecord.from_dict(_as_dict(r["data"])) for r in rows]

    async def list_pending_outbox(self) -> List[BuildRecord]:
        async with self._connect() as conn:
            rows = await conn.fetch(
                "SELECT data FROM app_build_sessions WHERE has_pending_outbox ORDER BY created_at LIMIT 500"
            )
        return [BuildRecord.from_dict(_as_dict(r["data"])) for r in rows]


def _as_dict(value: Any) -> dict:
    # With the jsonb codec registered asyncpg returns a dict; without it, a JSON string.
    return json.loads(value) if isinstance(value, (str, bytes)) else value
