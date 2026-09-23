from app.schemas.workflow import Action, FieldUpdate, Intent, Trigger, WorkflowState
from app.services.merger import apply_field_updates, merge_identified_list, merge_models


def test_merge_models_keeps_unset_fields():
    base = Trigger(kind="email.received", parameters={"folder": "Inbox"})
    incoming = Trigger.model_validate({"parameters": {"from": "billing@"}})
    merged = merge_models(base, incoming)
    assert merged.kind == "email.received"
    assert merged.parameters == {"folder": "Inbox", "from": "billing@"}


def test_merge_models_overwrites_when_user_changes_answer():
    base = Intent(summary="notify on invoice", tags=["finance"])
    incoming = Intent(summary="archive invoices instead")
    merged = merge_models(base, incoming)
    assert merged.summary == "archive invoices instead"
    assert merged.tags == ["finance"]


def test_merge_identified_list_updates_by_id_and_appends():
    existing = [Action(id="act_1", kind="notify.slack")]
    incoming = [
        Action(id="act_1", parameters={"channel": "#ops"}),
        Action(id="act_2", kind="sheets.append_row"),
    ]
    merged = merge_identified_list(existing, incoming, replace=False)
    assert [item.id for item in merged] == ["act_1", "act_2"]
    assert merged[0].kind == "notify.slack"
    assert merged[0].parameters["channel"] == "#ops"
    assert merged[1].kind == "sheets.append_row"


def test_merge_identified_list_replace():
    existing = [Action(id="act_1", kind="notify.slack")]
    incoming = [Action(id="act_9", kind="http.request")]
    merged = merge_identified_list(existing, incoming, replace=True)
    assert len(merged) == 1
    assert merged[0].kind == "http.request"


def test_field_updates_can_set_multiple_paths_and_grow_actions():
    state = WorkflowState()
    state = apply_field_updates(
        state,
        [
            FieldUpdate(path="intent.summary", value="sync orders to a sheet"),
            FieldUpdate(path="trigger.kind", value="shopify.order_created"),
            FieldUpdate(path="actions.0.kind", value="sheets.append_row"),
            FieldUpdate(path="actions.0.parameters.sheet", value="Orders"),
        ],
    )
    assert state.intent.summary == "sync orders to a sheet"
    assert state.trigger.kind == "shopify.order_created"
    assert state.actions[0].kind == "sheets.append_row"
    assert state.actions[0].parameters["sheet"] == "Orders"
