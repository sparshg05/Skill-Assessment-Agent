"""
Redis session store.
GraphState is serialised to JSON and stored per session_id.
Supports resumable sessions across multiple HTTP requests.
"""
from __future__ import annotations

import json
from typing import Any

import structlog
import redis.asyncio as aioredis

from config import get_settings
from models import GraphState, SessionPhase

logger = structlog.get_logger(__name__)

_redis_client: aioredis.Redis | None = None
_memory_sessions: dict[str, str] = {}


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


class SessionStore:
    """
    Thin wrapper around Redis for storing / retrieving GraphState.
    Uses session_id as the key with a configurable TTL.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.ttl = self.settings.session_ttl_seconds

    async def _client(self) -> aioredis.Redis:
        return await get_redis()

    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"

    async def save(self, state: GraphState) -> None:
        data = state.model_dump_json()
        key = self._key(state.session_id)
        try:
            client = await self._client()
            await client.setex(key, self.ttl, data)
            logger.debug("session_saved", session_id=state.session_id, phase=state.phase, backend="redis")
        except Exception as e:
            _memory_sessions[key] = data
            logger.warning(
                "session_saved_in_memory",
                session_id=state.session_id,
                phase=state.phase,
                error=str(e),
            )

    async def load(self, session_id: str) -> GraphState | None:
        key = self._key(session_id)
        raw: str | None = None
        try:
            client = await self._client()
            raw = await client.get(key)
        except Exception as e:
            raw = _memory_sessions.get(key)
            logger.warning("session_load_from_memory", session_id=session_id, error=str(e))

        if raw is None:
            logger.warning("session_not_found", session_id=session_id)
            return None
        state = GraphState.model_validate_json(raw)
        logger.debug("session_loaded", session_id=session_id, phase=state.phase)
        return state

    async def delete(self, session_id: str) -> None:
        key = self._key(session_id)
        try:
            client = await self._client()
            await client.delete(key)
        except Exception:
            _memory_sessions.pop(key, None)

    async def exists(self, session_id: str) -> bool:
        key = self._key(session_id)
        try:
            client = await self._client()
            return bool(await client.exists(key))
        except Exception:
            return key in _memory_sessions

    async def extend_ttl(self, session_id: str) -> None:
        key = self._key(session_id)
        try:
            client = await self._client()
            await client.expire(key, self.ttl)
        except Exception:
            # In-memory fallback currently has no TTL eviction.
            return


# Singleton
_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore()
    return _store