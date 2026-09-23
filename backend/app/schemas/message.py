from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class MessageRole(str, Enum):
    """Permitted message sender roles in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"


class ConversationMessageCreate(BaseModel):
    """Payload to create a new message in a conversation session."""

    model_config = ConfigDict(extra="forbid")

    role: MessageRole
    content: str = Field(..., min_length=1, description="Message text content")


class ConversationMessageResponse(BaseModel):
    """Serialized representation of a persisted conversation message."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    conversation_id: str
    role: MessageRole
    content: str
    created_at: datetime
