from app.schemas.workflow import (
    Action,
    Ambiguity,
    AmbiguityOption,
    Intent,
    Recipient,
    Schedule,
    Trigger,
    TriggerSource,
    WorkflowState,
)
from app.services.validator import has_unresolved_ambiguities, is_time_trigger, validate_state


def _complete_event_state(**kwargs) -> WorkflowState:
    data = dict(
        intent=Intent(summary="notify when a form is submitted"),
        trigger=Trigger(kind="form.submitted"),
        trigger_source=TriggerSource(kind="typeform", identifier="contact-form"),
        actions=[Action(id="act_1", kind="notify.email")],
    )
    data.update(kwargs)
    return WorkflowState(**data)


def test_empty_state_is_missing_intent_trigger_and_actions():
    missing = {item.path for item in validate_state(WorkflowState())}
    assert "intent.summary" in missing
    assert "trigger.kind" in missing
    assert "actions" in missing


def test_event_trigger_requires_source():
    state = _complete_event_state(trigger_source=TriggerSource())
    paths = {item.path for item in validate_state(state)}
    assert "trigger_source" in paths


def test_time_trigger_requires_schedule_not_source():
    state = WorkflowState(
        intent=Intent(summary="weekly digest"),
        trigger=Trigger(kind="schedule.cron"),
        actions=[Action(id="act_1", kind="email.send")],
    )
    paths = {item.path for item in validate_state(state)}
    assert "schedule" in paths
    assert "trigger_source" not in paths

    state.schedule = Schedule(frequency="weekly")
    assert validate_state(state) == []


def test_action_required_parameters_are_not_assumed():
    state = _complete_event_state(
        actions=[
            Action(
                id="act_1",
                kind="http.request",
                required_parameters=["url", "method"],
                parameters={"method": "POST"},
            )
        ]
    )
    missing = validate_state(state)
    assert any(item.path == "actions.0.parameters.url" for item in missing)


def test_needs_recipients_without_recipients():
    state = _complete_event_state(
        actions=[Action(id="act_1", kind="notify.chat", needs_recipients=True)],
        recipients=[],
    )
    assert any(item.path == "recipients" for item in validate_state(state))


def test_recipient_requires_channel_or_address():
    state = _complete_event_state(
        actions=[Action(id="act_1", kind="notify.chat", needs_recipients=True)],
        recipients=[Recipient(id="rcpt_1")],
    )
    assert any(item.path == "recipients.0" for item in validate_state(state))


def test_unresolved_ambiguity_detected():
    state = _complete_event_state(
        ambiguities=[
            Ambiguity(
                id="amb_1",
                path="trigger.kind",
                question="Which trigger?",
                options=[
                    AmbiguityOption(id="a", label="form"),
                    AmbiguityOption(id="b", label="email"),
                ],
            )
        ]
    )
    assert has_unresolved_ambiguities(state)


def test_is_time_trigger_is_generic():
    assert is_time_trigger("schedule.cron")
    assert is_time_trigger("interval")
    assert not is_time_trigger("email.received")
    assert not is_time_trigger("shopify.order_created")
