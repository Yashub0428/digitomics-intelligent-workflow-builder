import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db, get_llm_provider_dep
from app.db.models import Base
from app.main import app
from app.schemas.workflow import (
    Action,
    ConversationStatus,
    Intent,
    Recipient,
    Trigger,
    TriggerSource,
    WorkflowStatePatch,
)
from app.services.llm import LLMAPIError, MockLLMProvider


@pytest.fixture
def mock_llm():
    return MockLLMProvider()


@pytest.fixture
def test_client(mock_llm):
    """Create a TestClient with an isolated in-memory database and mock LLM provider."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_llm_provider_dep] = lambda: mock_llm

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_1_create_conversation_successfully(test_client):
    """Test 1: POST /api/conversations creates a session and returns 201."""
    resp = test_client.post("/api/conversations", json={"title": "Test Flow"})
    assert resp.status_code == 201
    data = resp.json()

    assert "conversation_id" in data
    assert data["phase"] == "COLLECTING"
    assert "created_at" in data
    assert "initial_state" in data


def test_2_create_conversation_initializes_valid_workflow_state(test_client):
    """Test 2: Initial state has COLLECTING status and missing mandatory fields."""
    resp = test_client.post("/api/conversations")
    assert resp.status_code == 201
    data = resp.json()

    state = data["initial_state"]
    assert state["status"] == "COLLECTING"
    assert len(state["missing_mandatory_fields"]) > 0


def test_3_send_message_to_valid_conversation(test_client, mock_llm):
    """Test 3: POST /api/conversations/{id}/messages processes user message."""
    conv_id = test_client.post("/api/conversations").json()["conversation_id"]

    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="notify on order"),
            trigger=Trigger(kind="order.created"),
            actions=[Action(id="act_1", kind="notify", needs_recipients=True)],
        )
    )

    resp = test_client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Whenever I receive an order, notify me."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["conversation_id"] == conv_id
    assert "assistant_message" in data
    assert data["status"] == "COLLECTING"


def test_4_send_message_returns_clarification_when_incomplete(test_client, mock_llm):
    """Test 4: Incomplete state returns clarification question and no workflow."""
    conv_id = test_client.post("/api/conversations").json()["conversation_id"]

    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="lead tracker"),
            trigger=Trigger(kind="lead.new"),
            actions=[Action(id="act_1", kind="slack.post")],
        )
    )

    resp = test_client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Track new leads and post to Slack"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COLLECTING"
    assert data["workflow"] is None
    assert len(data["missing_information"]) > 0


def test_5_send_multiple_messages_in_same_conversation(test_client, mock_llm):
    """Test 5: Multi-turn interaction preserves conversation and accumulates state."""
    conv_id = test_client.post("/api/conversations").json()["conversation_id"]

    # Turn 1: intent and trigger
    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="sync users"),
            trigger=Trigger(kind="user.signup"),
            trigger_source=TriggerSource(kind="auth0"),
        )
    )
    res1 = test_client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "When a user signs up in Auth0"},
    )
    assert res1.status_code == 200
    assert res1.json()["state"]["trigger"]["kind"] == "user.signup"

    # Turn 2: action
    mock_llm.set_response(
        WorkflowStatePatch(
            actions=[Action(id="act_1", kind="crm.create_contact")]
        )
    )
    res2 = test_client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Create a contact in the CRM"},
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "READY" or res2.json()["status"] == "GENERATED"


def test_6_complete_conversation_returns_generated_workflow(test_client, mock_llm):
    """Test 6: Providing complete information returns the generated workflow specification."""
    conv_id = test_client.post("/api/conversations").json()["conversation_id"]

    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="sync orders to sheets"),
            trigger=Trigger(kind="order.created"),
            trigger_source=TriggerSource(kind="shopify"),
            actions=[Action(id="act_1", kind="sheets.append")],
        )
    )

    resp = test_client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Sync Shopify orders to Google Sheets"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "GENERATED"
    assert data["workflow"] is not None
    assert data["workflow"]["name"] == "sync orders to sheets"


def test_7_workflow_is_not_returned_before_readiness(test_client):
    """Test 7: GET /workflow returns 400 when workflow has not yet been generated."""
    conv_id = test_client.post("/api/conversations").json()["conversation_id"]

    resp = test_client.get(f"/api/conversations/{conv_id}/workflow")
    assert resp.status_code == 400
    assert "Workflow has not been generated yet" in resp.json()["error"]["message"]


def test_8_get_messages_returns_chronological_history(test_client, mock_llm):
    """Test 8: GET /messages returns ordered user and assistant history."""
    conv_id = test_client.post("/api/conversations").json()["conversation_id"]

    mock_llm.set_response(WorkflowStatePatch(intent=Intent(summary="turn 1")))
    test_client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Turn 1"})

    mock_llm.set_response(WorkflowStatePatch(intent=Intent(summary="turn 2")))
    test_client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Turn 2"})

    resp = test_client.get(f"/api/conversations/{conv_id}/messages")
    assert resp.status_code == 200
    messages = resp.json()

    assert len(messages) == 4
    roles = [m["role"] for m in messages]
    assert roles == ["user", "assistant", "user", "assistant"]
    assert messages[0]["content"] == "Turn 1"
    assert messages[2]["content"] == "Turn 2"


def test_9_get_state_returns_current_state(test_client, mock_llm):
    """Test 9: GET /state returns the current WorkflowState."""
    conv_id = test_client.post("/api/conversations").json()["conversation_id"]

    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="nightly report"),
            trigger=Trigger(kind="schedule"),
        )
    )
    test_client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Nightly report"})

    resp = test_client.get(f"/api/conversations/{conv_id}/state")
    assert resp.status_code == 200
    data = resp.json()

    assert data["conversation_id"] == conv_id
    assert data["state"]["intent"]["summary"] == "nightly report"


def test_10_get_workflow_returns_generated_workflow(test_client, mock_llm):
    """Test 10: GET /workflow returns generated JSON once completed."""
    conv_id = test_client.post("/api/conversations").json()["conversation_id"]

    mock_llm.set_response(
        WorkflowStatePatch(
            intent=Intent(summary="completed flow"),
            trigger=Trigger(kind="webhook.call"),
            trigger_source=TriggerSource(kind="stripe"),
            actions=[Action(id="act_1", kind="log.write")],
        )
    )
    test_client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Log Stripe webhooks"})

    resp = test_client.get(f"/api/conversations/{conv_id}/workflow")
    assert resp.status_code == 200
    data = resp.json()

    assert data["conversation_id"] == conv_id
    assert data["status"] == "GENERATED"
    assert data["workflow"]["name"] == "completed flow"


def test_11_unknown_conversation_returns_404(test_client):
    """Test 11: Endpoints return 404 for unknown conversation IDs."""
    fake_id = "00000000-0000-0000-0000-000000000000"

    assert test_client.post(f"/api/conversations/{fake_id}/messages", json={"content": "hi"}).status_code == 404
    assert test_client.get(f"/api/conversations/{fake_id}/messages").status_code == 404
    assert test_client.get(f"/api/conversations/{fake_id}/state").status_code == 404
    assert test_client.get(f"/api/conversations/{fake_id}/workflow").status_code == 404


def test_12_blank_message_is_rejected(test_client):
    """Test 12: Blank or whitespace-only messages are rejected with 422."""
    conv_id = test_client.post("/api/conversations").json()["conversation_id"]

    resp = test_client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "     "},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_13_invalid_request_body_returns_validation_error(test_client):
    """Test 13: Malformed request payload returns 422 validation error."""
    conv_id = test_client.post("/api/conversations").json()["conversation_id"]

    resp = test_client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"wrong_key": 123},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_14_conversation_isolation_works(test_client, mock_llm):
    """Test 14: Conversations remain completely isolated."""
    c1 = test_client.post("/api/conversations").json()["conversation_id"]
    c2 = test_client.post("/api/conversations").json()["conversation_id"]

    mock_llm.set_response(WorkflowStatePatch(intent=Intent(summary="Conv 1 intent")))
    test_client.post(f"/api/conversations/{c1}/messages", json={"content": "Msg 1"})

    # Check c2 messages
    msgs_c2 = test_client.get(f"/api/conversations/{c2}/messages").json()
    assert len(msgs_c2) == 0

    state_c2 = test_client.get(f"/api/conversations/{c2}/state").json()["state"]
    assert state_c2["intent"]["summary"] is None


def test_15_llm_failure_is_handled_safely(test_client, mock_llm):
    """Test 15: LLM error during message processing falls back gracefully rather than crashing."""
    conv_id = test_client.post("/api/conversations").json()["conversation_id"]
    mock_llm.set_error(LLMAPIError("API rate limit exceeded"))

    resp = test_client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Backup database snapshots"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COLLECTING"
    assert "encountered an issue" in data["assistant_message"].lower()


def test_16_existing_exception_handlers_still_work(test_client):
    """Test 16: Standard error responses conform to ErrorResponse schema."""
    resp = test_client.get("/api/conversations/missing-session/state")
    assert resp.status_code == 404
    data = resp.json()

    assert "error" in data
    assert data["error"]["code"] == "http_error"
    assert "not found" in data["error"]["message"].lower()


def test_17_cors_configuration_does_not_break_application_startup(test_client):
    """Test 17: Pre-flight CORS request returns appropriate headers for local frontend."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
    }
    resp = test_client.options("/api/conversations", headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
