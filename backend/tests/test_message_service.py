from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base
from app.schemas.message import (
    ConversationMessageCreate,
    ConversationMessageResponse,
    MessageRole,
)
from app.services.message_service import (
    ConversationNotFoundError,
    add_message,
    create_session,
    get_messages,
)


@pytest.fixture
def db_session():
    """Create an isolated, in-memory SQLite database session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_create_user_message(db_session):
    """Test 1: Creating a user message."""
    conv = create_session(db_session)
    msg = add_message(
        db=db_session,
        conversation_id=conv.id,
        role=MessageRole.USER,
        content="I need a workflow to archive inbound emails to Google Drive.",
    )

    assert msg.id is not None
    assert msg.conversation_id == conv.id
    assert msg.role == "user"
    assert msg.content == "I need a workflow to archive inbound emails to Google Drive."
    assert isinstance(msg.created_at, datetime)

    # Verify Pydantic response schema validation
    resp = ConversationMessageResponse.model_validate(msg)
    assert resp.role == MessageRole.USER
    assert resp.content == msg.content
    assert resp.id == msg.id


def test_create_assistant_message(db_session):
    """Test 2: Creating an assistant message."""
    conv = create_session(db_session)
    msg = add_message(
        db=db_session,
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT,
        content="Which email folder should we watch for incoming messages?",
    )

    assert msg.id is not None
    assert msg.conversation_id == conv.id
    assert msg.role == "assistant"
    assert msg.content == "Which email folder should we watch for incoming messages?"

    resp = ConversationMessageResponse.model_validate(msg)
    assert resp.role == MessageRole.ASSISTANT


def test_retrieving_messages_in_chronological_order(db_session):
    """Test 3: Retrieving messages in chronological order."""
    conv = create_session(db_session)
    base_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Insert messages with explicit timestamps, out of sequential order
    msg2 = add_message(
        db_session,
        conv.id,
        MessageRole.ASSISTANT,
        "Second turn",
        created_at=base_time + timedelta(minutes=2),
    )
    msg1 = add_message(
        db_session,
        conv.id,
        MessageRole.USER,
        "First turn",
        created_at=base_time,
    )
    msg3 = add_message(
        db_session,
        conv.id,
        MessageRole.USER,
        "Third turn",
        created_at=base_time + timedelta(minutes=5),
    )

    history = get_messages(db_session, conv.id)
    assert len(history) == 3
    assert [m.id for m in history] == [msg1.id, msg2.id, msg3.id]
    assert history[0].content == "First turn"
    assert history[1].content == "Second turn"
    assert history[2].content == "Third turn"
    assert history[0].created_at < history[1].created_at < history[2].created_at


def test_multiple_messages_belonging_to_same_conversation(db_session):
    """Test 4: Multiple messages belonging to the same conversation."""
    conv = create_session(db_session)

    turns = [
        (MessageRole.USER, "Send a Slack message when a deal closes in HubSpot."),
        (MessageRole.ASSISTANT, "Which Slack channel should receive the notification?"),
        (MessageRole.USER, "Please send it to #sales-alerts."),
        (MessageRole.ASSISTANT, "Should we include deal value and owner name in the message?"),
    ]

    created = [
        add_message(db_session, conv.id, role, content)
        for role, content in turns
    ]

    # Verify via service retrieval
    history = get_messages(db_session, conv.id)
    assert len(history) == 4
    for i, (role, content) in enumerate(turns):
        assert history[i].role == role.value
        assert history[i].content == content

    # Verify via ORM relationship on ConversationSession
    db_session.refresh(conv)
    assert len(conv.messages) == 4
    assert [m.id for m in conv.messages] == [m.id for m in created]


def test_messages_from_different_conversations_remain_isolated(db_session):
    """Test 5: Messages from different conversations remaining isolated."""
    conv_a = create_session(db_session)
    conv_b = create_session(db_session)

    add_message(db_session, conv_a.id, MessageRole.USER, "Message A1")
    add_message(db_session, conv_a.id, MessageRole.ASSISTANT, "Message A2")

    add_message(db_session, conv_b.id, MessageRole.USER, "Message B1")
    add_message(db_session, conv_b.id, MessageRole.ASSISTANT, "Message B2")
    add_message(db_session, conv_b.id, MessageRole.USER, "Message B3")

    history_a = get_messages(db_session, conv_a.id)
    history_b = get_messages(db_session, conv_b.id)

    assert len(history_a) == 2
    assert [m.content for m in history_a] == ["Message A1", "Message A2"]
    assert all(m.conversation_id == conv_a.id for m in history_a)

    assert len(history_b) == 3
    assert [m.content for m in history_b] == ["Message B1", "Message B2", "Message B3"]
    assert all(m.conversation_id == conv_b.id for m in history_b)


def test_validation_and_error_handling(db_session):
    """Edge cases: non-existent session, invalid roles, blank content, schema validation."""
    conv = create_session(db_session)

    # Non-existent session
    with pytest.raises(ConversationNotFoundError):
        add_message(db_session, "non-existent-id", MessageRole.USER, "Hello")

    with pytest.raises(ConversationNotFoundError):
        get_messages(db_session, "non-existent-id")

    # Invalid role
    with pytest.raises(ValueError, match="Invalid message role"):
        add_message(db_session, conv.id, "system", "System prompt")

    # Empty content
    with pytest.raises(ValueError, match="Message content cannot be empty"):
        add_message(db_session, conv.id, MessageRole.USER, "   ")

    # Pydantic schema validation errors
    with pytest.raises(ValidationError):
        ConversationMessageCreate(role="unknown", content="Hello")

    with pytest.raises(ValidationError):
        ConversationMessageCreate(role=MessageRole.USER, content="")
