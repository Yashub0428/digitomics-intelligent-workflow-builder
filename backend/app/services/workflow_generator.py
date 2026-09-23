import uuid
from typing import Any

from app.schemas.workflow import ConversationStatus, WorkflowState


class WorkflowGeneratorError(ValueError):
    """Raised when workflow generation is requested on an incomplete state."""


class WorkflowGenerator:
    """
    Transforms a complete, validated WorkflowState into a final
    structured workflow representation.
    """

    def generate_workflow(self, state: WorkflowState) -> dict[str, Any]:
        """
        Generate the final structured workflow specification.
        Never invents fields or integrations not present in the validated state.
        """
        if state.status not in (ConversationStatus.READY, ConversationStatus.GENERATED):
            raise WorkflowGeneratorError(
                f"Cannot generate workflow from state with status '{state.status.value}'. "
                "State must be READY with all mandatory fields collected and ambiguities resolved."
            )

        trigger_data: dict[str, Any] = {
            "kind": state.trigger.kind,
            "parameters": state.trigger.parameters,
        }
        if state.trigger_source.kind or state.trigger_source.identifier:
            trigger_data["source"] = state.trigger_source.model_dump(exclude_unset=True)
        if state.schedule:
            trigger_data["schedule"] = state.schedule.model_dump(exclude_unset=True)

        workflow: dict[str, Any] = {
            "id": f"wf_{uuid.uuid4().hex[:10]}",
            "name": state.intent.summary or "Automated Workflow",
            "status": "ready",
            "schema_version": state.schema_version,
            "intent": state.intent.model_dump(exclude_unset=True),
            "trigger": trigger_data,
            "conditions": [c.model_dump(exclude_unset=True) for c in state.conditions],
            "actions": [a.model_dump(exclude_unset=True) for a in state.actions],
            "recipients": [r.model_dump(exclude_unset=True) for r in state.recipients],
            "preferences": state.preferences.model_dump(exclude_unset=True),
        }
        return workflow

    def generate_confirmation_message(
        self,
        state: WorkflowState,
        workflow: dict[str, Any],
    ) -> str:
        """Create a polite confirmation message summarizing the finalized workflow."""
        summary = state.intent.summary or "your requested automation"
        action_count = len(state.actions)
        return (
            f"Your workflow for '{summary}' is complete and validated with {action_count} "
            f"action{'s' if action_count != 1 else ''}. The final structured workflow has been generated."
        )
