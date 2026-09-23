import logging
from typing import Any

from app.schemas.clarification import ClarificationQuestion
from app.schemas.workflow import WorkflowState
from app.services.llm.base import LLMProvider
from app.services.prompts import (
    CLARIFICATION_SYSTEM_PROMPT,
    build_clarification_messages,
)

logger = logging.getLogger(__name__)


class ClarificationEngine:
    """
    Determines and generates the next focused clarification question
    when the workflow state is incomplete or contains ambiguities.
    """

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def generate_question(
        self,
        state: WorkflowState,
        history: list[Any] | None = None,
    ) -> ClarificationQuestion:
        """
        Identify the single highest-priority missing fact or ambiguity
        and formulate a human-friendly clarification question.
        """
        # 1. Check for unresolved ambiguities (highest priority)
        unresolved_ambiguity = next(
            (amb for amb in state.ambiguities if not amb.resolved),
            None,
        )

        if unresolved_ambiguity:
            target_field = unresolved_ambiguity.path
            reason = f"Resolving ambiguity: {unresolved_ambiguity.question}"
            options = [opt.label for opt in unresolved_ambiguity.options]
            if options:
                deterministic_q = (
                    f"{unresolved_ambiguity.question} "
                    f"Options: {', '.join(options)}."
                )
            else:
                deterministic_q = unresolved_ambiguity.question

            return self._formulate_question(
                state=state,
                target_field=target_field,
                reason=reason,
                deterministic_fallback=deterministic_q,
                options=options,
                history=history,
            )

        # 2. Check missing mandatory fields
        if not state.missing_mandatory_fields:
            return ClarificationQuestion(
                question="The workflow is complete. No further information is needed.",
                target_field="",
                reason="All mandatory information is collected",
            )

        sorted_missing = sorted(
            state.missing_mandatory_fields,
            key=lambda m: self._field_priority(m.path),
        )
        top_missing = sorted_missing[0]
        target_field = top_missing.path
        reason = top_missing.reason
        deterministic_q = self._deterministic_fallback_question(state, target_field, reason)

        return self._formulate_question(
            state=state,
            target_field=target_field,
            reason=reason,
            deterministic_fallback=deterministic_q,
            options=[],
            history=history,
        )

    def _field_priority(self, path: str) -> int:
        """Assign deterministic priority ranks to missing paths."""
        if path.startswith("intent"):
            return 1
        if path.startswith("trigger.kind"):
            return 2
        if path.startswith("trigger_source"):
            return 3
        if path.startswith("schedule"):
            return 4
        if path == "actions":
            return 5
        if ".kind" in path:
            return 6
        if ".parameters." in path:
            return 7
        if path.startswith("recipients"):
            return 8
        if path.startswith("conditions"):
            return 9
        return 10

    def _deterministic_fallback_question(
        self,
        state: WorkflowState,
        path: str,
        reason: str,
    ) -> str:
        """Formulate a clean, natural question for standard missing fields without LLM."""
        if path.startswith("intent"):
            return "What would you like this automation workflow to accomplish?"

        if path.startswith("trigger.kind"):
            return "What event or trigger should start this workflow?"

        if path.startswith("trigger_source"):
            if state.trigger.kind:
                return f"Which platform or service should provide the {state.trigger.kind} event?"
            return "Which platform or service should trigger this workflow?"

        if path.startswith("schedule"):
            return "When or how often should this workflow run?"

        if path == "actions":
            return "What action should the workflow take when triggered?"

        if ".kind" in path:
            return "What specific action should be performed for this step?"

        if ".parameters." in path:
            param_key = path.split(".parameters.")[-1]
            readable_param = param_key.replace("_", " ")
            return f"What {readable_param} should be used for this action?"

        if path == "recipients" or path.startswith("recipients."):
            return "Where or to which recipient should the notification be sent?"

        if path.startswith("conditions."):
            return "What condition or rule must be met before this step proceeds?"

        return f"Please specify the required {path.split('.')[-1]} ({reason})."

    def _formulate_question(
        self,
        state: WorkflowState,
        target_field: str,
        reason: str,
        deterministic_fallback: str,
        options: list[str],
        history: list[Any] | None,
    ) -> ClarificationQuestion:
        """Attempt LLM question generation with automatic fallback to deterministic question."""
        if self.provider is not None:
            try:
                messages = build_clarification_messages(
                    state=state,
                    target_field=target_field,
                    reason=reason,
                    options=options,
                    history=history,
                )
                generated = self.provider.generate_structured(
                    messages=messages,
                    response_schema=ClarificationQuestion,
                    system_instruction=CLARIFICATION_SYSTEM_PROMPT,
                )
                if generated.question and generated.question.strip():
                    return generated
            except Exception as exc:
                logger.warning(
                    "LLM clarification question generation failed, using deterministic fallback: %s",
                    exc,
                )

        return ClarificationQuestion(
            question=deterministic_fallback,
            target_field=target_field,
            reason=reason,
            options=options,
        )
