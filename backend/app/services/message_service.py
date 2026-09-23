import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ConversationMessage, ConversationSession
from app.schemas.message import MessageRole


class ConversationNotFoundError(ValueError):
    """Raised when an operation targets a non-existent conversation session."""


def create_session(
    db: Session,
    session_id: str | None = None,
    phase: str = "idle",
    state_json: str = "{}",
) -> ConversationSession:
    """Create and persist a new conversation session."""
    session = ConversationSession(
        id=session_id or str(uuid.uuid4()),
        phase=phase,
        state_json=state_json,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def add_message(
    db: Session,
    conversation_id: str,
    role: MessageRole | str,
    content: str,
    created_at: datetime | None = None,
) -> ConversationMessage:
    """
    Persist a message to the conversation history.

    Validates that:
    1. The conversation session exists.
    2. The role is valid ('user' or 'assistant').
    3. The content is non-empty.
    """
    session = db.get(ConversationSession, conversation_id)
    if session is None:
        raise ConversationNotFoundError(
            f"Conversation session '{conversation_id}' not found"
        )

    if isinstance(role, MessageRole):
        role_str = role.value
    elif isinstance(role, str):
        try:
            role_str = MessageRole(role.strip().lower()).value
        except ValueError:
            raise ValueError(
                f"Invalid message role '{role}'. Must be 'user' or 'assistant'."
            )
    else:
        raise ValueError("Role must be an instance of MessageRole or str ('user' | 'assistant')")

    cleaned_content = content.strip()
    if not cleaned_content:
        raise ValueError("Message content cannot be empty")

    message_kwargs = {
        "conversation_id": conversation_id,
        "role": role_str,
        "content": cleaned_content,
    }
    if created_at is not None:
        message_kwargs["created_at"] = created_at

    message = ConversationMessage(**message_kwargs)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_messages(
    db: Session,
    conversation_id: str,
) -> list[ConversationMessage]:
    """
    Retrieve all messages for a given conversation session in chronological order.
    """
    session = db.get(ConversationSession, conversation_id)
    if session is None:
        raise ConversationNotFoundError(
            f"Conversation session '{conversation_id}' not found"
        )

    stmt = (
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())
    )
    return list(db.scalars(stmt).all())
