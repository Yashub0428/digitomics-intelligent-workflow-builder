import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, ConversationSession
from app.schemas.clarification import ClarificationQuestion
from app.schemas.workflow import (
    Action,
    Ambiguity,
    AmbiguityOption,
    AmbiguityResolution,
    Condition,
    ConversationStatus,
    FieldUpdate,
    Intent,
    Recipient,
    Trigger,
    TriggerSource,
    WorkflowStatePatch,
)
from app.services.clarification import ClarificationEngine
from app.services.extraction import ExtractionService
from app.services.llm import LLMAPIError, LLMTimeoutError, MockLLMProvider
from app.services.message_service import create_session, get_messages
from app.services.orchestrator import ConversationOrchestrator
from app.services.state_manager import WorkflowStateManager
from app.services.workflow_generator import WorkflowGenerator


@pytest.fixture
def db_session():
    """Create an isolated, in-memory SQLite database session for orchestrator tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_llm():
    return MockLLMProvider()


@pytest.fixture
def orchestrator(db_session, mock_llm):
    extraction = ExtractionService(provider=mock_llm)
    clarification = ClarificationEngine(provider=mock_llm)
    return ConversationOrchestrator(
        db=db_session,
        extraction_service=extraction,
        clarification_engine=clarification,
    )


def test_1_initial_incomplete_request_asks_clarification(orchestrator, db_session, mock_llm):
    """Test 1: Initial incomplete request asks a focused clarification question."""
    conv = create_session(db_session)
    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="notify on incoming invoices"),
            trigger=Trigger(kind="invoice.received"),
            actions=[Action(id="act_1", kind="notify", needs_recipients=True)],
        )
    )

    result = orchestrator.process_message(conv.id, "Whenever I receive an invoice, notify me.")

    assert result.status == ConversationStatus.COLLECTING
    assert result.workflow is None
    assert len(result.missing_information) > 0
    assert result.assistant_message is not None
    assert len(result.assistant_message) > 5


def test_2_multiple_facts_reduce_clarification_questions(orchestrator, db_session, mock_llm):
    """Test 2: Supplying multiple facts produces a ready workflow in a single turn."""
    conv = create_session(db_session)
    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="archive Shopify orders to Google Sheets"),
            trigger=Trigger(kind="shopify.order_created"),
            trigger_source=TriggerSource(kind="shopify", identifier="main-store"),
            actions=[Action(id="act_1", kind="sheets.append_row")],
        )
    )

    result = orchestrator.process_message(
        conv.id,
        "When an order is created on Shopify store main-store, append a row to Google Sheets.",
    )

    assert result.status == ConversationStatus.GENERATED
    assert result.workflow is not None
    assert result.workflow["name"] == "archive Shopify orders to Google Sheets"
    assert result.missing_information == []


def test_3_missing_trigger_source_generates_appropriate_question(orchestrator, db_session, mock_llm):
    """Test 3: Missing trigger source produces a targeted source clarification question."""
    conv = create_session(db_session)
    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="forward alerts"),
            trigger=Trigger(kind="alert.fired"),
            actions=[Action(id="act_1", kind="slack.post")],
        )
    )

    result = orchestrator.process_message(conv.id, "Forward alerts to Slack")
    assert result.status == ConversationStatus.COLLECTING
    assert any(m.path == "trigger_source" for m in result.missing_information)
    # The question should ask about platform or source
    assert "platform" in result.assistant_message.lower() or "service" in result.assistant_message.lower()


def test_4_missing_recipient_generates_appropriate_question(orchestrator, db_session, mock_llm):
    """Test 4: Missing recipient produces a targeted recipient clarification question."""
    conv = create_session(db_session)
    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="email alerts on failure"),
            trigger=Trigger(kind="build.failed"),
            trigger_source=TriggerSource(kind="github"),
            actions=[Action(id="act_1", kind="email.send", needs_recipients=True)],
        )
    )

    result = orchestrator.process_message(conv.id, "Send an email when a build fails on GitHub")
    assert result.status == ConversationStatus.COLLECTING
    assert any(m.path == "recipients" for m in result.missing_information)
    assert "recipient" in result.assistant_message.lower() or "where" in result.assistant_message.lower()


def test_5_missing_action_parameter_generates_appropriate_question(orchestrator, db_session, mock_llm):
    """Test 5: Missing required action parameter produces targeted parameter question."""
    conv = create_session(db_session)
    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="trigger webhook"),
            trigger=Trigger(kind="order.paid"),
            trigger_source=TriggerSource(kind="stripe"),
            actions=[
                Action(
                    id="act_1",
                    kind="http.post",
                    required_parameters=["target_url"],
                    parameters={},
                )
            ],
        )
    )

    result = orchestrator.process_message(conv.id, "Send an HTTP POST when order is paid in Stripe")
    assert result.status == ConversationStatus.COLLECTING
    assert any(m.path == "actions.0.parameters.target_url" for m in result.missing_information)
    assert "target url" in result.assistant_message.lower()


def test_6_unresolved_ambiguity_blocks_workflow_generation(orchestrator, db_session, mock_llm):
    """Test 6: Unresolved ambiguity blocks readiness and is asked to the user."""
    conv = create_session(db_session)
    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="notify team"),
            trigger=Trigger(kind="issue.opened"),
            trigger_source=TriggerSource(kind="github"),
            actions=[Action(id="act_1", kind="notify")],
            ambiguities=[
                Ambiguity(
                    id="amb_channel",
                    path="actions.0.kind",
                    question="Where should we notify the team?",
                    options=[
                        AmbiguityOption(id="slack", label="Slack"),
                        AmbiguityOption(id="email", label="Email"),
                    ],
                )
            ],
        )
    )

    result = orchestrator.process_message(conv.id, "Notify the team on new issue")
    assert result.status == ConversationStatus.COLLECTING
    assert result.workflow is None
    assert result.ambiguity is not None
    assert result.ambiguity.id == "amb_channel"
    assert "Slack" in result.assistant_message


def test_7_ambiguity_resolution_allows_progress(orchestrator, db_session, mock_llm):
    """Test 7: Resolving ambiguity allows transitioning to READY/GENERATED."""
    conv = create_session(db_session)

    # Turn 1: Ambiguous request
    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="alert on down"),
            trigger=Trigger(kind="server.down"),
            trigger_source=TriggerSource(kind="datadog"),
            actions=[Action(id="act_1", kind="notify")],
            ambiguities=[
                Ambiguity(
                    id="amb_channel",
                    path="actions.0.kind",
                    question="Which notification tool?",
                    options=[
                        AmbiguityOption(id="slack", label="Slack"),
                        AmbiguityOption(id="pagerduty", label="PagerDuty"),
                    ],
                )
            ],
        )
    )
    res1 = orchestrator.process_message(conv.id, "Alert the team when server is down")
    assert res1.status == ConversationStatus.COLLECTING

    # Turn 2: User resolves ambiguity
    mock_llm.set_response(
        WorkflowStatePatch(
            resolve_ambiguities=[AmbiguityResolution(ambiguity_id="amb_channel", chosen="slack")],
            field_updates=[FieldUpdate(path="actions.0.kind", value="notify.slack")],
        )
    )
    res2 = orchestrator.process_message(conv.id, "Use Slack")
    assert res2.status == ConversationStatus.GENERATED
    assert res2.workflow is not None
    assert res2.state.actions[0].kind == "notify.slack"
    assert res2.state.ambiguities[0].resolved is True


def test_8_user_correction_updates_existing_state(orchestrator, db_session, mock_llm):
    """Test 8: User correction successfully updates previous state."""
    conv = create_session(db_session)

    # Turn 1
    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="sync leads"),
            trigger=Trigger(kind="lead.created"),
            trigger_source=TriggerSource(kind="salesforce"),
            actions=[Action(id="act_1", kind="sheets.append")],
        )
    )
    res1 = orchestrator.process_message(conv.id, "Sync Salesforce leads to sheets")
    assert res1.state.trigger_source.kind == "salesforce"

    # Turn 2: Correction
    mock_llm.set_response(
        WorkflowStatePatch(
            trigger_source=TriggerSource(kind="hubspot"),
            field_updates=[FieldUpdate(path="trigger_source.kind", value="hubspot")],
        )
    )
    res2 = orchestrator.process_message(conv.id, "Actually, use HubSpot instead of Salesforce")
    assert res2.state.trigger_source.kind == "hubspot"
    assert res2.state.intent.summary == "sync leads"


def test_9_complete_workflow_generates_final_workflow(orchestrator, db_session, mock_llm):
    """Test 9: Complete state generates final structured workflow JSON."""
    conv = create_session(db_session)
    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="high value customer alert"),
            trigger=Trigger(kind="customer.signed_up"),
            trigger_source=TriggerSource(kind="stripe"),
            conditions=[Condition(id="c1", expression="plan == 'enterprise'")],
            actions=[Action(id="act_1", kind="slack.message", parameters={"channel": "#vip"})],
        )
    )

    result = orchestrator.process_message(conv.id, "Send Slack message to #vip for enterprise signup on Stripe")
    assert result.status == ConversationStatus.GENERATED
    assert result.workflow is not None
    assert result.workflow["name"] == "high value customer alert"
    assert result.workflow["trigger"]["kind"] == "customer.signed_up"
    assert result.workflow["conditions"][0]["expression"] == "plan == 'enterprise'"
    assert result.workflow["actions"][0]["kind"] == "slack.message"


def test_10_workflow_is_not_generated_while_validator_reports_missing_fields(
    orchestrator, db_session, mock_llm
):
    """Test 10: Workflow generation is strictly blocked when missing mandatory fields exist."""
    conv = create_session(db_session)
    # Only intent is provided
    mock_llm.set_response(
        WorkflowStatePatch(intent=Intent(summary="automate my customer pipeline"))
    )

    result = orchestrator.process_message(conv.id, "I want to automate my pipeline")
    assert result.status == ConversationStatus.COLLECTING
    assert result.workflow is None
    assert len(result.missing_information) >= 2


def test_11_llm_clarification_failure_uses_deterministic_fallback(db_session):
    """Test 11: LLM failure during clarification question generation falls back gracefully."""
    extraction_llm = MockLLMProvider()
    extraction_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="backup database"),
            trigger=Trigger(kind="schedule.cron"),
            actions=[Action(id="act_1", kind="backup.run")],
        )
    )

    clarification_llm = MockLLMProvider()
    clarification_llm.set_error(LLMAPIError("Clarification model unreachable"))

    orch = ConversationOrchestrator(
        db=db_session,
        extraction_service=ExtractionService(extraction_llm),
        clarification_engine=ClarificationEngine(clarification_llm),
    )
    conv = create_session(db_session)


    # Missing schedule since trigger is schedule.cron
    result = orch.process_message(conv.id, "Backup database on schedule")
    assert result.status == ConversationStatus.COLLECTING
    # Must use deterministic fallback question rather than crashing
    assert "when or how often" in result.assistant_message.lower()


def test_12_llm_workflow_generation_failure_is_handled_safely(db_session, mock_llm):
    """Test 12: Errors in workflow formatting do not corrupt state or crash."""
    class FailingGenerator(WorkflowGenerator):
        def generate_workflow(self, state):
            raise RuntimeError("Unexpected workflow formatting crash")

    orch = ConversationOrchestrator(
        db=db_session,
        extraction_service=ExtractionService(mock_llm),
        clarification_engine=ClarificationEngine(mock_llm),
        workflow_generator=FailingGenerator(),
    )
    conv = create_session(db_session)
    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="ping service"),
            trigger=Trigger(kind="heartbeat"),
            trigger_source=TriggerSource(kind="datadog"),
            actions=[Action(id="act_1", kind="ping")],
        )
    )

    result = orch.process_message(conv.id, "Ping on heartbeat")
    # State remains intact and system returns controlled message
    assert "error occurred while formatting" in result.assistant_message
    assert result.workflow is None


def test_13_user_message_is_persisted(orchestrator, db_session, mock_llm):
    """Test 13: User message is properly stored in conversation_messages."""
    conv = create_session(db_session)
    mock_llm.set_response(WorkflowStatePatch())

    orchestrator.process_message(conv.id, "Hello, workflow builder!")
    messages = get_messages(db_session, conv.id)

    assert any(m.role == "user" and m.content == "Hello, workflow builder!" for m in messages)


def test_14_assistant_message_is_persisted(orchestrator, db_session, mock_llm):
    """Test 14: Assistant message is properly stored in conversation_messages."""
    conv = create_session(db_session)
    mock_llm.set_response(WorkflowStatePatch())

    result = orchestrator.process_message(conv.id, "Need an automation")
    messages = get_messages(db_session, conv.id)

    assert any(m.role == "assistant" and m.content == result.assistant_message for m in messages)


def test_15_conversation_history_remains_isolated_by_conversation_id(
    orchestrator, db_session, mock_llm
):
    """Test 15: Two distinct conversation sessions remain completely isolated."""
    conv1 = create_session(db_session)
    conv2 = create_session(db_session)

    mock_llm.set_response(WorkflowStatePatch(intent=Intent(summary="Conversation 1 workflow")))
    orchestrator.process_message(conv1.id, "Message in conv 1")

    mock_llm.set_response(WorkflowStatePatch(intent=Intent(summary="Conversation 2 workflow")))
    orchestrator.process_message(conv2.id, "Message in conv 2")

    msgs1 = get_messages(db_session, conv1.id)
    msgs2 = get_messages(db_session, conv2.id)

    assert all(m.conversation_id == conv1.id for m in msgs1)
    assert all(m.conversation_id == conv2.id for m in msgs2)
    assert not any(m.content == "Message in conv 2" for m in msgs1)


def test_16_repeated_turns_preserve_state_correctly(orchestrator, db_session, mock_llm):
    """Test 16: Multi-turn flow incrementally accumulates workflow facts."""
    conv = create_session(db_session)

    # Turn 1: Intent & trigger
    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="sync tickets"),
            trigger=Trigger(kind="ticket.created"),
            trigger_source=TriggerSource(kind="zendesk"),
        )
    )
    res1 = orchestrator.process_message(conv.id, "Sync new Zendesk tickets")
    assert res1.status == ConversationStatus.COLLECTING
    assert res1.state.trigger.kind == "ticket.created"

    # Turn 2: Action
    mock_llm.set_response(
        WorkflowStatePatch(
            actions=[Action(id="act_1", kind="slack.post", needs_recipients=True)]
        )
    )
    res2 = orchestrator.process_message(conv.id, "Post a message to Slack")
    assert res2.status == ConversationStatus.COLLECTING
    assert res2.state.trigger.kind == "ticket.created"
    assert res2.state.actions[0].kind == "slack.post"

    # Turn 3: Recipient
    mock_llm.set_response(
        WorkflowStatePatch(
            recipients=[Recipient(id="rcpt_1", channel="slack", address="#support-team")]
        )
    )
    res3 = orchestrator.process_message(conv.id, "Send to #support-team")
    assert res3.status == ConversationStatus.GENERATED
    assert res3.workflow is not None
    assert res3.workflow["recipients"][0]["address"] == "#support-team"


def test_17_empty_input_is_handled_safely(orchestrator, db_session, mock_llm):
    """Test 17: Empty or whitespace input does not crash and leaves state uncorrupted."""
    conv = create_session(db_session)
    result = orchestrator.process_message(conv.id, "   ")

    assert result.status == ConversationStatus.COLLECTING
    assert "didn't receive any details" in result.assistant_message
    assert result.workflow is None
    # No user message was persisted for blank input
    messages = get_messages(db_session, conv.id)
    assert not any(m.role == "user" for m in messages)


def test_18_llm_timeout_triggers_deterministic_fallback(orchestrator, db_session, mock_llm):
    """Test 18: LLMTimeoutError during extraction triggers deterministic fallback without crashing."""
    conv = create_session(db_session)
    mock_llm.set_error(LLMTimeoutError("Gemini request timed out: deadline exceeded"))

    result = orchestrator.process_message(conv.id, "When an invoice arrives notify team")

    assert result.status == ConversationStatus.COLLECTING
    assert "encountered an issue processing that message" in result.assistant_message
    assert result.workflow is None
    # User message was preserved
    messages = get_messages(db_session, conv.id)
    assert any(m.role == "user" and m.content == "When an invoice arrives notify team" for m in messages)
    assert any(m.role == "assistant" for m in messages)
