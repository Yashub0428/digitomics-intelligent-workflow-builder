from app.schemas.workflow import (
    Action,
    MissingField,
    WorkflowState,
)

TIME_TRIGGER_KINDS = frozenset({
    "schedule",
    "schedule.cron",
    "cron",
    "interval",
    "timer",
    "time",
})


def is_time_trigger(kind: str | None) -> bool:
    if not kind:
        return False
    normalized = kind.lower().replace("-", ".").replace("_", ".")
    return normalized in TIME_TRIGGER_KINDS or normalized.startswith("schedule.")


def _blank(value: str | None) -> bool:
    return value is None or not str(value).strip()


def validate_state(state: WorkflowState) -> list[MissingField]:
    """
    Deterministic completeness check. Never fills defaults.

    Rules are structural and catalog-agnostic so new trigger/action kinds work
    without code changes. Per-action `required_parameters` and `needs_recipients`
    let later phases (catalog/LLM) declare extra mandates.
    """
    missing: list[MissingField] = []

    if _blank(state.intent.summary):
        missing.append(MissingField(
            path="intent.summary",
            reason="User intent is required",
        ))

    if _blank(state.trigger.kind):
        missing.append(MissingField(
            path="trigger.kind",
            reason="A trigger kind is required",
        ))
    elif is_time_trigger(state.trigger.kind):
        if state.schedule is None or (
            _blank(state.schedule.frequency) and _blank(state.schedule.cron)
        ):
            missing.append(MissingField(
                path="schedule",
                reason="Time-based triggers require a user-stated frequency or cron expression",
            ))
    elif _blank(state.trigger_source.kind) and _blank(state.trigger_source.identifier):
        missing.append(MissingField(
            path="trigger_source",
            reason="Event triggers require a source kind or identifier",
        ))

    if not state.actions:
        missing.append(MissingField(
            path="actions",
            reason="At least one action is required",
        ))
    else:
        for index, action in enumerate(state.actions):
            missing.extend(_action_missing(action, index))

    needs_recipients = any(action.needs_recipients for action in state.actions)
    if needs_recipients and not state.recipients:
        missing.append(MissingField(
            path="recipients",
            reason="At least one recipient is required by an action",
        ))
    else:
        for index, recipient in enumerate(state.recipients):
            if _blank(recipient.channel) and _blank(recipient.address):
                missing.append(MissingField(
                    path=f"recipients.{index}",
                    reason="Each recipient needs a channel or address",
                ))

    for index, condition in enumerate(state.conditions):
        if _blank(condition.expression):
            missing.append(MissingField(
                path=f"conditions.{index}.expression",
                reason="Each condition needs a user-stated expression",
            ))

    return missing


def _action_missing(action: Action, index: int) -> list[MissingField]:
    missing: list[MissingField] = []
    prefix = f"actions.{index}"
    if _blank(action.kind):
        missing.append(MissingField(
            path=f"{prefix}.kind",
            reason="Each action needs a kind",
        ))
    for key in action.required_parameters:
        value = action.parameters.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(MissingField(
                path=f"{prefix}.parameters.{key}",
                reason=f"Action parameter '{key}' is required and was not provided",
            ))
    return missing


def has_unresolved_ambiguities(state: WorkflowState) -> bool:
    return any(not item.resolved for item in state.ambiguities)
