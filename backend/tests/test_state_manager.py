import pytest

from app.schemas.workflow import (
    Action,
    Ambiguity,
    AmbiguityOption,
    AmbiguityResolution,
    ConversationStatus,
    FieldUpdate,
    Intent,
    Recipient,
    Trigger,
    TriggerSource,
    WorkflowStatePatch,
)
from app.services.state_manager import StateTransitionError, WorkflowStateManager


def test_create_starts_collecting_with_missing_fields():
    state = WorkflowStateManager().create()
    assert state.status == ConversationStatus.COLLECTING
    assert state.missing_mandatory_fields


def test_one_message_can_supply_multiple_facts():
    manager = WorkflowStateManager()
    state = manager.create()
    state = manager.apply(
        state,
        WorkflowStatePatch(
            intent=Intent(summary="append new store orders to a spreadsheet"),
            trigger=Trigger(kind="shopify.order_created"),
            trigger_source=TriggerSource(kind="shopify", identifier="main-store"),
            actions=[Action(id="act_1", kind="sheets.append_row")],
            field_updates=[
                FieldUpdate(path="actions.0.parameters.sheet", value="Orders"),
                FieldUpdate(path="preferences.timezone", value="America/New_York"),
            ],
        ),
        utterance_id="u1",
    )
    assert state.status == ConversationStatus.READY
    assert state.intent.summary.startswith("append new store")
    assert state.trigger.kind == "shopify.order_created"
    assert state.actions[0].parameters["sheet"] == "Orders"
    assert state.preferences.timezone == "America/New_York"
    assert "intent.summary" in state.collected
    assert state.collected["intent.summary"].utterance_id == "u1"


def test_user_can_change_a_previous_answer():
    manager = WorkflowStateManager()
    state = manager.create()
    state = manager.apply(
        state,
        WorkflowStatePatch(
            intent=Intent(summary="notify ops when a server is down"),
            trigger=Trigger(kind="monitoring.alert"),
            trigger_source=TriggerSource(identifier="pagerduty"),
            actions=[Action(id="act_1", kind="notify.slack", parameters={"channel": "#alerts"})],
        ),
        utterance_id="u1",
    )
    state = manager.apply(
        state,
        WorkflowStatePatch(
            actions=[Action(id="act_1", parameters={"channel": "#incidents"})],
            field_updates=[FieldUpdate(path="trigger_source.identifier", value="datadog")],
        ),
        utterance_id="u2",
    )
    assert state.actions[0].kind == "notify.slack"
    assert state.actions[0].parameters["channel"] == "#incidents"
    assert state.trigger_source.identifier == "datadog"
    assert state.collected["trigger_source.identifier"].utterance_id == "u2"
    assert state.status == ConversationStatus.READY


def test_ambiguity_blocks_ready_until_resolved():
    manager = WorkflowStateManager()
    state = manager.create()
    state = manager.apply(
        state,
        WorkflowStatePatch(
            intent=Intent(summary="tell the team about new tickets"),
            trigger=Trigger(kind="ticket.created"),
            trigger_source=TriggerSource(kind="jira", identifier="OPS"),
            actions=[Action(id="act_1", kind="notify")],
            ambiguities=[
                Ambiguity(
                    id="amb_channel",
                    path="actions.0.kind",
                    question="Where should we notify the team?",
                    options=[
                        AmbiguityOption(id="slack", label="Slack"),
                        AmbiguityOption(id="teams", label="Teams"),
                    ],
                )
            ],
        ),
    )
    assert state.status == ConversationStatus.COLLECTING

    state = manager.apply(
        state,
        WorkflowStatePatch(
            resolve_ambiguities=[
                AmbiguityResolution(ambiguity_id="amb_channel", chosen="slack")
            ],
            field_updates=[FieldUpdate(path="actions.0.kind", value="notify.slack")],
        ),
    )
    assert state.ambiguities[0].resolved is True
    assert state.status == ConversationStatus.READY


def test_mark_generated_requires_ready_and_edits_reset_status():
    manager = WorkflowStateManager()
    state = manager.create()
    with pytest.raises(StateTransitionError):
        manager.mark_generated(state)

    state = manager.apply(
        state,
        WorkflowStatePatch(
            intent=Intent(summary="mirror CRM contacts into a warehouse"),
            trigger=Trigger(kind="crm.contact_updated"),
            trigger_source=TriggerSource(kind="hubspot"),
            actions=[Action(id="act_1", kind="warehouse.upsert")],
        ),
    )
    generated = manager.mark_generated(state)
    assert generated.status == ConversationStatus.GENERATED

    edited = manager.apply(
        generated,
        WorkflowStatePatch(
            field_updates=[FieldUpdate(path="actions.0.kind", value="warehouse.insert")],
        ),
    )
    assert edited.status == ConversationStatus.READY
    assert edited.actions[0].kind == "warehouse.insert"


def test_recipients_and_conditions_from_a_non_email_domain():
    manager = WorkflowStateManager()
    state = manager.apply(
        manager.create(),
        WorkflowStatePatch(
            intent=Intent(summary="page on-call when queue depth is high"),
            trigger=Trigger(kind="metrics.threshold"),
            trigger_source=TriggerSource(kind="prometheus", identifier="job=worker"),
            actions=[
                Action(
                    id="act_1",
                    kind="pagerduty.trigger",
                    needs_recipients=True,
                    required_parameters=["severity"],
                    parameters={"severity": "critical"},
                )
            ],
            recipients=[Recipient(id="rcpt_1", channel="pagerduty", address="payments-oncall")],
            field_updates=[
                FieldUpdate(path="conditions.0.expression", value="queue_depth > 1000 for 5m"),
            ],
        ),
    )
    assert state.status == ConversationStatus.READY
    assert state.conditions[0].expression.startswith("queue_depth")
    assert state.recipients[0].address == "payments-oncall"
