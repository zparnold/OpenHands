# IMPORTANT: LEGACY V0 CODE - Deprecated since version 1.0.0, scheduled for removal April 1, 2026
# This file is part of the legacy (V0) implementation of OpenHands and will be removed soon as we complete the migration to V1.
# OpenHands V1 uses the Software Agent SDK for the agentic core and runs a new application server. Please refer to:
#   - V1 agentic core (SDK): https://github.com/OpenHands/software-agent-sdk
#   - V1 application server (in this repo): openhands/app_server/
# Unless you are working on deprecation, please avoid extending this legacy file and consult the V1 codepaths above.
# Tag: Legacy-V0
# This module belongs to the old V0 web server. The V1 application server lives under openhands/app_server/.
import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from openhands.core.logger import openhands_logger as logger
from openhands.server.shared import (
    ConversationStoreImpl,
    config,
    conversation_manager,
    server_config,
)
from openhands.server.user_auth import get_user_id
from openhands.storage.conversation.conversation_store import ConversationStore
from openhands.storage.conversation.postgres_conversation_store import (
    PostgresConversationStore,
)
from openhands.storage.data_models.conversation_metadata import ConversationMetadata


def validate_conversation_id(conversation_id: str) -> str:
    """
    Validate conversation ID format and length.

    Args:
        conversation_id: The conversation ID to validate

    Returns:
        The validated conversation ID

    Raises:
        HTTPException: If the conversation ID is invalid
    """
    # Check length - UUID hex is 32 characters, allow some flexibility but not excessive
    if len(conversation_id) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Conversation ID is too long',
        )

    # Check for null bytes and other problematic characters
    if '\x00' in conversation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Conversation ID contains invalid characters',
        )

    # Check for path traversal attempts
    if '..' in conversation_id or '/' in conversation_id or '\\' in conversation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Conversation ID contains invalid path characters',
        )

    # Check for control characters and newlines
    if any(ord(c) < 32 for c in conversation_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Conversation ID contains control characters',
        )

    return conversation_id


def _use_postgres_conversation_store() -> bool:
    return (
        ConversationStoreImpl is PostgresConversationStore
        or 'postgres' in server_config.conversation_store_class.lower()
    )


async def _db_session_dependency(request: Request) -> AsyncSession:
    """Lazy dependency: imports app_server.config only at request time."""
    from openhands.app_server.config import get_db_session

    async with get_db_session(request.state, request) as session:
        yield session


async def _get_conversation_store_file(request: Request) -> ConversationStore | None:
    conversation_store: ConversationStore | None = getattr(
        request.state, 'conversation_store', None
    )
    if conversation_store:
        return conversation_store
    user_id = await get_user_id(request)
    conversation_store = await ConversationStoreImpl.get_instance(config, user_id)
    request.state.conversation_store = conversation_store
    return conversation_store


async def _get_conversation_store_postgres(
    user_id: str | None = Depends(get_user_id),
    db_session: AsyncSession = Depends(_db_session_dependency),
) -> ConversationStore | None:
    return PostgresConversationStore(db_session, user_id)


if _use_postgres_conversation_store():
    get_conversation_store = _get_conversation_store_postgres  # type: ignore[assignment]
else:

    async def get_conversation_store(  # type: ignore[assignment,misc]
        request: Request,
    ) -> ConversationStore | None:
        return await _get_conversation_store_file(request)


async def generate_unique_conversation_id(
    conversation_store: ConversationStore,
) -> str:
    conversation_id = uuid.uuid4().hex
    while await conversation_store.exists(conversation_id):
        conversation_id = uuid.uuid4().hex
    return conversation_id


async def get_conversation_metadata(
    conversation_id: str,
    conversation_store: ConversationStore = Depends(get_conversation_store),
) -> ConversationMetadata:
    """Get conversation metadata and validate user access without requiring an active conversation."""
    try:
        metadata = await conversation_store.get_metadata(conversation_id)
        return metadata
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Conversation {conversation_id} not found',
        )


async def get_conversation(
    conversation_id: str, user_id: str | None = Depends(get_user_id)
):
    """Grabs conversation id set by middleware. Adds the conversation_id to the openapi schema."""
    conversation = await conversation_manager.attach_to_conversation(
        conversation_id, user_id
    )
    if not conversation:
        logger.warning(
            f'get_conversation: conversation {conversation_id} not found, attach_to_conversation returned None',
            extra={'session_id': conversation_id, 'user_id': user_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Conversation {conversation_id} not found',
        )
    try:
        yield conversation
    finally:
        await conversation_manager.detach_from_conversation(conversation)
