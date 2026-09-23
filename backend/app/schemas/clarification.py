from pydantic import BaseModel, ConfigDict, Field


class ClarificationQuestion(BaseModel):
    """Structured clarification question emitted when workflow state is incomplete."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., description="Human-friendly clarification question")
    target_field: str = Field(..., description="Path of the missing or ambiguous field being clarified")
    reason: str = Field(..., description="Why this information is required")
    options: list[str] = Field(default_factory=list, description="Candidate choices if resolving an ambiguity")
