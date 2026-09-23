from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.workflow import Ambiguity, ConversationStatus, MissingField, WorkflowState


class ConversationTurnResult(BaseModel):
    """Result of processing a single conversation message turn."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    assistant_message: str
    status: ConversationStatus
    workflow: dict[str, Any] | None = None
    missing_information: list[MissingField] = Field(default_factory=list)
    ambiguity: Ambiguity | None = None
    state: WorkflowState
