"""SaaS session tracking helpers for V0 conversation managers."""

from __future__ import annotations

import logging

from starlette.datastructures import State

from openhands.server.config.server_config import ServerConfig
from openhands.server.types import AppMode
from openhands.storage.sessions.postgres_session_store import PostgresSessionStore

logger = logging.getLogger(__name__)


async def upsert_saas_session(
    server_config: ServerConfig,
    session_id: str,
    user_id: str | None,
    conversation_id: str | None = None,
    state: dict | None = None,
    user_email: str | None = None,
    user_display_name: str | None = None,
) -> None:
    """Persist SaaS session metadata when Postgres is enabled."""
    if server_config.app_mode != AppMode.SAAS or not user_id:
        return

    try:
        from openhands.app_server.config import get_db_session

        state_obj = State()
        async with get_db_session(state_obj, None) as db_session:
            store = PostgresSessionStore(db_session)
            await store.upsert_session(
                session_id=session_id,
                user_id=user_id,
                conversation_id=conversation_id,
                state=state,
                user_email=user_email,
                user_display_name=user_display_name,
            )
    except Exception as exc:
        logger.warning(
            'Failed to persist SaaS session metadata',
            extra={
                'session_id': session_id,
                'user_id': user_id,
                'error': str(exc),
            },
        )
