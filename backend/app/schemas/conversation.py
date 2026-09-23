from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.workflow import WorkflowState


class ConversationCreateRequest(BaseModel):
    """Payload to start a new workflow builder conversation."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(
        default=None,
        max_length=200,
        description="Optional title or user description for the conversation",
    )


class ConversationCreateResponse(BaseModel):
    """Metadata and initial state returned upon conversation creation."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    phase: str
    created_at: datetime
    initial_state: WorkflowState


class MessageSendRequest(BaseModel):
    """Payload when a user sends a message to a conversation."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User natural-language input message",
    )

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message content cannot be blank or whitespace only")
        return stripped


class WorkflowStateResponse(BaseModel):
    """Response containing the current WorkflowState of a conversation."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    state: WorkflowState


class WorkflowResponse(BaseModel):
    """Response containing the final generated workflow JSON specification."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    status: str
    workflow: dict[str, Any]
