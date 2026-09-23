from typing import Any

from app.db.models import ConversationMessage
from app.schemas.workflow import WorkflowState, WorkflowStatePatch
from app.services.llm.base import LLMProvider
from app.services.prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    build_extraction_messages,
)


class ExtractionService:
    """
    Orchestrates the conversion of natural-language messages into
    validated structured WorkflowStatePatch instances via an LLM provider.
    """

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def extract_patch(
        self,
        user_message: str,
        conversation_history: list[ConversationMessage] | list[dict[str, Any]] | None = None,
        current_state: WorkflowState | None = None,
    ) -> WorkflowStatePatch:
        """
        Extract structured workflow facts from a user message.

        Args:
            user_message: The raw natural language input from the user.
            conversation_history: Prior conversation turns as ORM messages or dicts.
            current_state: Existing workflow state for context.

        Returns:
            A validated WorkflowStatePatch.

        Raises:
            LLMResponseValidationError: If LLM output fails schema validation.
            LLMError: If the underlying LLM provider encounters an error.
        """
        cleaned = user_message.strip() if user_message else ""
        if not cleaned:
            return WorkflowStatePatch()

        normalized_history: list[dict[str, Any]] = []
        if conversation_history:
            for item in conversation_history:
                if isinstance(item, ConversationMessage):
                    normalized_history.append({"role": item.role, "content": item.content})
                elif isinstance(item, dict):
                    normalized_history.append(item)

        messages = build_extraction_messages(
            user_message=cleaned,
            conversation_history=normalized_history,
            current_state=current_state,
        )

        patch = self.provider.generate_structured(
            messages=messages,
            response_schema=WorkflowStatePatch,
            system_instruction=EXTRACTION_SYSTEM_PROMPT,
        )

        return patch
