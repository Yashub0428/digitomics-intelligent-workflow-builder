import pytest

from app.schemas.workflow import (
    Action,
    Ambiguity,
    AmbiguityOption,
    Condition,
    ConversationStatus,
    FieldUpdate,
    Intent,
    Recipient,
    Schedule,
    Trigger,
    TriggerSource,
    WorkflowStatePatch,
)
from app.services.extraction import ExtractionService
from app.services.llm import (
    LLMAPIError,
    LLMResponseValidationError,
    MockLLMProvider,
)
from app.services.state_manager import WorkflowStateManager


@pytest.fixture
def mock_llm():
    return MockLLMProvider()


@pytest.fixture
def extraction_service(mock_llm):
    return ExtractionService(provider=mock_llm)


def test_1_mock_provider_returns_valid_structured_output(extraction_service, mock_llm):
    """Test 1: Mock provider returns valid structured output."""
    expected_patch = WorkflowStatePatch(
        intent=Intent(summary="sync tickets to spreadsheet", tags=["support"])
    )
    mock_llm.set_response(expected_patch)

    patch = extraction_service.extract_patch("Sync support tickets to a sheet")
    assert isinstance(patch, WorkflowStatePatch)
    assert patch.intent.summary == "sync tickets to spreadsheet"
    assert patch.intent.tags == ["support"]
    assert mock_llm.call_count == 1


def test_2_extraction_of_intent(extraction_service, mock_llm):
    """Test 2: Extraction of intent."""
    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(
                summary="backup database snapshots daily to S3",
                tags=["database", "backup", "aws"],
            )
        )
    )

    patch = extraction_service.extract_patch("I need to backup database snapshots daily to S3")
    assert patch.intent is not None
    assert patch.intent.summary == "backup database snapshots daily to S3"
    assert "aws" in patch.intent.tags


def test_3_extraction_of_trigger(extraction_service, mock_llm):
    """Test 3: Extraction of trigger."""
    mock_llm.set_response(
        WorkflowStatePatch(
            trigger=Trigger(kind="webhook.received", parameters={"path": "/orders/webhook"})
        )
    )

    patch = extraction_service.extract_patch("Trigger when a webhook arrives at /orders/webhook")
    assert patch.trigger is not None
    assert patch.trigger.kind == "webhook.received"
    assert patch.trigger.parameters["path"] == "/orders/webhook"


def test_4_extraction_of_trigger_source(extraction_service, mock_llm):
    """Test 4: Extraction of trigger source."""
    mock_llm.set_response(
        WorkflowStatePatch(
            trigger_source=TriggerSource(kind="stripe", identifier="acct_live_9941")
        )
    )

    patch = extraction_service.extract_patch("Listen for events from Stripe account acct_live_9941")
    assert patch.trigger_source is not None
    assert patch.trigger_source.kind == "stripe"
    assert patch.trigger_source.identifier == "acct_live_9941"


def test_5_extraction_of_schedule(extraction_service, mock_llm):
    """Test 5: Extraction of schedule."""
    mock_llm.set_response(
        WorkflowStatePatch(
            trigger=Trigger(kind="schedule"),
            schedule=Schedule(frequency="weekly", cron="0 9 * * 1", timezone="UTC"),
        )
    )

    patch = extraction_service.extract_patch("Run this every Monday at 9am UTC")
    assert patch.schedule is not None
    assert patch.schedule.frequency == "weekly"
    assert patch.schedule.cron == "0 9 * * 1"
    assert patch.schedule.timezone == "UTC"


def test_6_extraction_of_actions(extraction_service, mock_llm):
    """Test 6: Extraction of actions without assuming unstated parameters."""
    mock_llm.set_response(
        WorkflowStatePatch(
            actions=[
                Action(
                    id="act_send_email",
                    kind="email.send",
                    needs_recipients=True,
                    required_parameters=["subject", "body"],
                    parameters={},
                )
            ]
        )
    )

    patch = extraction_service.extract_patch("Send an email")
    assert len(patch.actions) == 1
    action = patch.actions[0]
    assert action.kind == "email.send"
    assert action.needs_recipients is True
    assert action.required_parameters == ["subject", "body"]
    # Subject and body must not be invented
    assert action.parameters == {}


def test_7_extraction_of_recipients(extraction_service, mock_llm):
    """Test 7: Extraction of recipients."""
    mock_llm.set_response(
        WorkflowStatePatch(
            recipients=[
                Recipient(
                    id="rcpt_1",
                    channel="email",
                    address="devops-oncall@example.com",
                )
            ]
        )
    )

    patch = extraction_service.extract_patch("Send notifications to devops-oncall@example.com")
    assert len(patch.recipients) == 1
    assert patch.recipients[0].channel == "email"
    assert patch.recipients[0].address == "devops-oncall@example.com"


def test_8_extraction_of_conditions(extraction_service, mock_llm):
    """Test 8: Extraction of conditions."""
    mock_llm.set_response(
        WorkflowStatePatch(
            conditions=[
                Condition(
                    id="cond_amount",
                    expression="invoice.amount > 10000",
                )
            ]
        )
    )

    patch = extraction_service.extract_patch("Only proceed if invoice amount is over 10000")
    assert len(patch.conditions) == 1
    assert patch.conditions[0].expression == "invoice.amount > 10000"


def test_9_multiple_facts_in_one_message(extraction_service, mock_llm):
    """Test 9: Multiple facts extracted from a single message and applied to state."""
    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="alert on high value invoices"),
            trigger=Trigger(kind="invoice.created"),
            trigger_source=TriggerSource(kind="quickbooks", identifier="company_123"),
            conditions=[Condition(id="cond_1", expression="invoice.amount > 50000")],
            actions=[
                Action(
                    id="act_slack",
                    kind="slack.message",
                    needs_recipients=True,
                    parameters={"text": "High value invoice created"},
                )
            ],
            recipients=[Recipient(id="rcpt_slack", channel="slack", address="#finance-alerts")],
        )
    )

    patch = extraction_service.extract_patch(
        "When an invoice over 50000 is created in QuickBooks company_123, send a Slack message to #finance-alerts"
    )

    # Verify all parts extracted in single turn
    assert patch.intent.summary == "alert on high value invoices"
    assert patch.trigger.kind == "invoice.created"
    assert patch.trigger_source.kind == "quickbooks"
    assert patch.conditions[0].expression == "invoice.amount > 50000"
    assert patch.actions[0].kind == "slack.message"
    assert patch.recipients[0].address == "#finance-alerts"

    # Verify compatibility with existing WorkflowStateManager
    manager = WorkflowStateManager()
    state = manager.apply(manager.create(), patch)
    assert state.status == ConversationStatus.READY
    assert state.trigger.kind == "invoice.created"
    assert state.actions[0].kind == "slack.message"


def test_10_user_correction(extraction_service, mock_llm):
    """Test 10: User correction of a previous fact."""
    manager = WorkflowStateManager()
    initial_patch = WorkflowStatePatch(
        intent=Intent(summary="sync orders"),
        trigger=Trigger(kind="order.created"),
        trigger_source=TriggerSource(kind="shopify", identifier="store_a"),
        actions=[Action(id="act_1", kind="sheets.append_row")],
    )
    state = manager.apply(manager.create(), initial_patch)
    assert state.trigger_source.kind == "shopify"

    # User corrects: "Actually, use WooCommerce instead of Shopify"
    mock_llm.set_response(
        WorkflowStatePatch(
            trigger_source=TriggerSource(kind="woocommerce", identifier="store_b"),
            field_updates=[FieldUpdate(path="trigger_source.kind", value="woocommerce")],
        )
    )

    correction_patch = extraction_service.extract_patch(
        "Actually, use WooCommerce store_b instead of Shopify",
        current_state=state,
    )
    updated_state = manager.apply(state, correction_patch)
    assert updated_state.trigger_source.kind == "woocommerce"
    assert updated_state.trigger_source.identifier == "store_b"
    # Prior intent and actions preserved
    assert updated_state.intent.summary == "sync orders"
    assert updated_state.actions[0].kind == "sheets.append_row"


def test_11_ambiguous_request(extraction_service, mock_llm):
    """Test 11: Ambiguous request produces Ambiguity object."""
    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="notify team on new lead"),
            trigger=Trigger(kind="crm.lead_created"),
            trigger_source=TriggerSource(kind="salesforce"),
            actions=[Action(id="act_1", kind="notify", needs_recipients=True)],
            ambiguities=[
                Ambiguity(
                    id="amb_channel",
                    path="actions.0.kind",
                    question="Which channel should be used to notify the team?",
                    options=[
                        AmbiguityOption(id="slack", label="Slack"),
                        AmbiguityOption(id="email", label="Email"),
                        AmbiguityOption(id="teams", label="Microsoft Teams"),
                    ],
                )
            ],
        )
    )

    patch = extraction_service.extract_patch("Notify the team when a new lead is created in Salesforce")
    assert len(patch.ambiguities) == 1
    amb = patch.ambiguities[0]
    assert amb.id == "amb_channel"
    assert amb.resolved is False
    assert len(amb.options) == 3
    assert {opt.id for opt in amb.options} == {"slack", "email", "teams"}

    # Apply to state and verify ambiguity blocks READY
    manager = WorkflowStateManager()
    state = manager.apply(manager.create(), patch)
    assert state.status == ConversationStatus.COLLECTING


def test_12_missing_information_is_not_invented(extraction_service, mock_llm):
    """Test 12: Missing information is NOT assumed or defaulted."""
    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="notify me when an invoice arrives"),
            trigger=Trigger(kind="invoice.received"),
            # No trigger_source assumed (e.g. Gmail was NOT invented)
            actions=[
                Action(
                    id="act_1",
                    kind="notify",
                    needs_recipients=True,
                    required_parameters=["subject", "body"],
                    parameters={},
                )
            ],
            # No recipients assumed (Slack / Email NOT invented)
            recipients=[],
        )
    )

    patch = extraction_service.extract_patch("Whenever I receive an invoice, notify me.")
    assert patch.trigger_source is None
    assert patch.recipients == []
    assert patch.actions[0].parameters == {}

    # State manager and validator must detect missing trigger_source and recipients
    manager = WorkflowStateManager()
    state = manager.apply(manager.create(), patch)
    assert state.status == ConversationStatus.COLLECTING
    missing_paths = {m.path for m in state.missing_mandatory_fields}
    assert "trigger_source" in missing_paths
    assert "recipients" in missing_paths


def test_13_invalid_structured_output(extraction_service, mock_llm):
    """Test 13: Invalid structured output from LLM raises LLMResponseValidationError."""
    # Forbidden extra field or wrong data type
    mock_llm.set_response({"intent": {"summary": 12345, "invalid_field": "disallowed"}})

    with pytest.raises(LLMResponseValidationError):
        extraction_service.extract_patch("Do something invalid")


def test_14_llm_provider_failure(extraction_service, mock_llm):
    """Test 14: LLM/provider failure raises controlled LLM exception."""
    mock_llm.set_error(LLMAPIError("Provider connection reset by peer"))

    with pytest.raises(LLMAPIError, match="connection reset"):
        extraction_service.extract_patch("Trigger on new commit")


def test_15_empty_or_irrelevant_user_message(extraction_service, mock_llm):
    """Test 15: Empty or irrelevant user messages do not invent workflow items."""
    # Blank user message returns empty patch immediately without calling LLM
    empty_patch = extraction_service.extract_patch("    ")
    assert isinstance(empty_patch, WorkflowStatePatch)
    assert empty_patch.intent is None
    assert empty_patch.trigger is None
    assert mock_llm.call_count == 0

    # Irrelevant message: mock returns empty patch
    mock_llm.set_response(WorkflowStatePatch())
    greeting_patch = extraction_service.extract_patch("Hello there!")
    assert greeting_patch.intent is None
    assert greeting_patch.trigger is None
    assert greeting_patch.actions is None
