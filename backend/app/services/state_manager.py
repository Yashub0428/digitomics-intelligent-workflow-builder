import time

from app.schemas.workflow import (
    Ambiguity,
    ConversationStatus,
    WorkflowState,
    WorkflowStatePatch,
)
from app.services.merger import (
    apply_field_updates,
    collect_from_patch,
    merge_ambiguities,
    merge_identified_list,
    merge_models,
    record_collected,
    set_path,
)
from app.services.validator import has_unresolved_ambiguities, validate_state


class StateTransitionError(ValueError):
    """Raised when a status change is not allowed."""


class WorkflowStateManager:
    """Owns create / merge / validate. Does not talk to an LLM."""

    def __init__(self) -> None:
        self.last_merge_duration: float = 0.0
        self.last_validation_duration: float = 0.0

    def create(self) -> WorkflowState:
        state = WorkflowState()
        return self._refresh(state)

    def apply(
        self,
        state: WorkflowState,
        patch: WorkflowStatePatch,
        utterance_id: str | None = None,
    ) -> WorkflowState:
        """
        Merge every fact from one user turn, then re-validate.

        Multiple field_updates and nested objects in the same patch are all applied.
        Later field_updates override earlier assignments to the same path.
        New values overwrite previously collected slots at the same path.
        """
        t_merge_start = time.perf_counter()
        next_state = state.model_copy(deep=True)

        if patch.intent is not None:
            next_state.intent = merge_models(next_state.intent, patch.intent)
        if patch.trigger is not None:
            next_state.trigger = merge_models(next_state.trigger, patch.trigger)
        if patch.trigger_source is not None:
            next_state.trigger_source = merge_models(
                next_state.trigger_source, patch.trigger_source
            )
        if patch.schedule is not None:
            if next_state.schedule is None:
                next_state.schedule = patch.schedule
            else:
                next_state.schedule = merge_models(next_state.schedule, patch.schedule)
        if patch.preferences is not None:
            next_state.preferences = merge_models(next_state.preferences, patch.preferences)

        if patch.conditions is not None:
            next_state.conditions = merge_identified_list(
                next_state.conditions,
                patch.conditions,
                replace=patch.replace_conditions,
            )
        if patch.actions is not None:
            next_state.actions = merge_identified_list(
                next_state.actions,
                patch.actions,
                replace=patch.replace_actions,
            )
        if patch.recipients is not None:
            next_state.recipients = merge_identified_list(
                next_state.recipients,
                patch.recipients,
                replace=patch.replace_recipients,
            )

        if patch.remove_condition_ids:
            next_state.conditions = [
                item for item in next_state.conditions if item.id not in patch.remove_condition_ids
            ]
        if patch.remove_action_ids:
            next_state.actions = [
                item for item in next_state.actions if item.id not in patch.remove_action_ids
            ]
        if patch.remove_recipient_ids:
            next_state.recipients = [
                item for item in next_state.recipients if item.id not in patch.remove_recipient_ids
            ]

        preexisting_unresolved = {
            item.id for item in next_state.ambiguities if not item.resolved
        }

        if patch.ambiguities is not None:
            next_state.ambiguities = merge_ambiguities(next_state.ambiguities, patch.ambiguities)

        for resolution in patch.resolve_ambiguities:
            next_state = self._resolve_ambiguity(
                next_state,
                resolution.ambiguity_id,
                resolution.chosen,
                utterance_id,
            )

        if patch.field_updates:
            next_state = apply_field_updates(next_state, patch.field_updates)

        collect_from_patch(next_state, patch, utterance_id)
        self._auto_resolve_ambiguities(next_state, eligible_ids=preexisting_unresolved)
        self.last_merge_duration = time.perf_counter() - t_merge_start
        return self._refresh(next_state)

    def mark_generated(self, state: WorkflowState) -> WorkflowState:
        next_state = self._refresh(state.model_copy(deep=True))
        if next_state.status != ConversationStatus.READY:
            raise StateTransitionError(
                "Workflow can be marked GENERATED only when status is READY"
            )
        next_state.status = ConversationStatus.GENERATED
        return next_state

    def _resolve_ambiguity(
        self,
        state: WorkflowState,
        ambiguity_id: str,
        chosen: str,
        utterance_id: str | None = None,
    ) -> WorkflowState:
        found = False
        target_path: str | None = None
        updated: list[Ambiguity] = []
        for item in state.ambiguities:
            if item.id == ambiguity_id:
                found = True
                target_path = item.path
                updated.append(item.model_copy(update={"resolved": True, "chosen": chosen}))
            else:
                updated.append(item)
        if not found:
            raise StateTransitionError(f"Unknown ambiguity id {ambiguity_id!r}")
        state.ambiguities = updated
        if target_path:
            state = set_path(state, target_path, chosen)
            record_collected(state, target_path, chosen, utterance_id)
        return state

    def _auto_resolve_ambiguities(
        self,
        state: WorkflowState,
        eligible_ids: set[str],
    ) -> None:
        """Resolve only ambiguities that existed before this turn.

        A new ambiguity must not be closed by the same message that raised it.
        """
        collected_paths = set(state.collected)
        resolved: list[Ambiguity] = []
        for item in state.ambiguities:
            if (
                not item.resolved
                and item.id in eligible_ids
                and item.path in collected_paths
            ):
                value = state.collected[item.path].value
                resolved.append(item.model_copy(update={
                    "resolved": True,
                    "chosen": str(value),
                }))
            else:
                resolved.append(item)
        state.ambiguities = resolved

    def _refresh(self, state: WorkflowState) -> WorkflowState:
        t_val_start = time.perf_counter()
        state.missing_mandatory_fields = validate_state(state)
        complete = not state.missing_mandatory_fields and not has_unresolved_ambiguities(state)
        self.last_validation_duration = time.perf_counter() - t_val_start
        if complete:
            # Any merge re-opens the plan. GENERATED is only set by mark_generated().
            state.status = ConversationStatus.READY
        else:
            state.status = ConversationStatus.COLLECTING
        return state
