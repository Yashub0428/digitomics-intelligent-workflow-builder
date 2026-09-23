import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_orchestrator
from app.db.models import ConversationSession
from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationCreateResponse,
    MessageSendRequest,
    WorkflowResponse,
    WorkflowStateResponse,
)
from app.schemas.message import ConversationMessageResponse
from app.schemas.orchestrator import ConversationTurnResult
from app.schemas.workflow import ConversationStatus, WorkflowState
from app.services.message_service import (
    ConversationNotFoundError,
    create_session,
    get_messages,
)
from app.services.orchestrator import ConversationOrchestrator
from app.services.state_manager import WorkflowStateManager
from app.services.workflow_generator import WorkflowGenerator

logger = logging.getLogger(__name__)
router = APIRouter(tags=["conversations"])


@router.post(
    "/conversations",
    response_model=ConversationCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workflow builder conversation",
    description="Initializes a new conversation session with an empty, validated initial workflow state.",
)
def create_conversation(
    payload: ConversationCreateRequest | None = None,
    db: Session = Depends(get_db),
) -> ConversationCreateResponse:
    state_manager = WorkflowStateManager()
    initial_state = state_manager.create()

    session = create_session(
        db=db,
        phase=initial_state.status.value,
        state_json=initial_state.model_dump_json(),
    )

    return ConversationCreateResponse(
        conversation_id=session.id,
        phase=session.phase,
        created_at=session.created_at,
        initial_state=initial_state,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationTurnResult,
    status_code=status.HTTP_200_OK,
    summary="Send a message to a conversation",
    description="Processes user input via the orchestrator: extracts facts, merges state, checks validity, and either asks clarification or finalizes the workflow.",
)
def send_message(
    conversation_id: str,
    payload: MessageSendRequest,
    orchestrator: ConversationOrchestrator = Depends(get_orchestrator),
) -> ConversationTurnResult:
    t_req_start = time.perf_counter()
    try:
        result = orchestrator.process_message(
            conversation_id=conversation_id,
            user_message=payload.content,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    finally:
        t_req_total = time.perf_counter() - t_req_start
        timings = getattr(orchestrator, "last_timings", {})
        t_extract = timings.get("gemini_extraction", 0.0)
        t_merge = timings.get("state_merge", 0.0)
        t_val = timings.get("validation", 0.0)
        t_clarify = timings.get("gemini_clarification", 0.0)
        t_persist = timings.get("persistence", 0.0)
        t_retry = timings.get("retry_wait", 0.0)

        timing_report = (
            f"\n================ TIMING BREAKDOWN ================\n"
            f"Request total:          {t_req_total:.2f}s\n"
            f"Gemini extraction:      {t_extract:.2f}s\n"
            f"State merge:            {t_merge:.4f}s\n"
            f"Validation:             {t_val:.4f}s\n"
            f"Gemini clarification:   {t_clarify:.2f}s\n"
            f"Persistence:            {t_persist:.4f}s\n"
            f"Retries/backoff wait:   {t_retry:.4f}s\n"
            f"=================================================="
        )
        print(timing_report, flush=True)
        logger.info(timing_report)

    return result


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[ConversationMessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Get conversation message history",
    description="Retrieves all messages for the specified conversation session in chronological order.",
)
def get_conversation_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> list[ConversationMessageResponse]:
    try:
        messages = get_messages(db=db, conversation_id=conversation_id)
        return [ConversationMessageResponse.model_validate(m) for m in messages]
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/conversations/{conversation_id}/state",
    response_model=WorkflowStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current workflow state",
    description="Returns the full WorkflowState associated with this conversation session.",
)
def get_workflow_state(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> WorkflowStateResponse:
    session = db.get(ConversationSession, conversation_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation session '{conversation_id}' not found",
        )

    if session.state_json and session.state_json.strip() and session.state_json != "{}":
        state = WorkflowState.model_validate_json(session.state_json)
    else:
        state = WorkflowStateManager().create()

    return WorkflowStateResponse(
        conversation_id=conversation_id,
        state=state,
    )


@router.get(
    "/conversations/{conversation_id}/workflow",
    response_model=WorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Get generated workflow specification",
    description="Returns the final generated structured workflow specification if completed. Returns HTTP 400 if state is still incomplete.",
)
def get_generated_workflow(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> WorkflowResponse:
    session = db.get(ConversationSession, conversation_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation session '{conversation_id}' not found",
        )

    if session.state_json and session.state_json.strip() and session.state_json != "{}":
        state = WorkflowState.model_validate_json(session.state_json)
    else:
        state = WorkflowStateManager().create()

    if state.status != ConversationStatus.GENERATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Workflow has not been generated yet. Current status is '{state.status.value}'. "
                "All mandatory information must be collected and ambiguities resolved first."
            ),
        )

    generator = WorkflowGenerator()
    workflow_data = generator.generate_workflow(state)

    return WorkflowResponse(
        conversation_id=conversation_id,
        status=state.status.value,
        workflow=workflow_data,
    )
