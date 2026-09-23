import logging
import time
from sqlalchemy.orm import Session

from app.db.models import ConversationSession
from app.schemas.message import MessageRole
from app.schemas.orchestrator import ConversationTurnResult
from app.schemas.workflow import ConversationStatus, WorkflowState
from app.services.clarification import ClarificationEngine
from app.services.extraction import ExtractionService
from app.services.llm.base import LLMProvider
from app.services.llm.exceptions import LLMError
from app.services.message_service import (
    ConversationNotFoundError,
    add_message,
    get_messages,
)
from app.services.state_manager import WorkflowStateManager
from app.services.workflow_generator import WorkflowGenerator

logger = logging.getLogger(__name__)


class ConversationOrchestrator:
    """
    Coordinates message persistence, information extraction, state management,
    deterministic validation, clarification generation, and workflow finalization.
    """

    def __init__(
        self,
        db: Session,
        extraction_service: ExtractionService | None = None,
        clarification_engine: ClarificationEngine | None = None,
        workflow_generator: WorkflowGenerator | None = None,
        state_manager: WorkflowStateManager | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.db = db
        self.last_timings: dict[str, float] = {}
        self.state_manager = state_manager or WorkflowStateManager()
        self.workflow_generator = workflow_generator or WorkflowGenerator()

        if extraction_service is not None:
            self.extraction_service = extraction_service
        elif llm_provider is not None:
            self.extraction_service = ExtractionService(provider=llm_provider)
        else:
            raise ValueError("Either extraction_service or llm_provider must be provided")

        if clarification_engine is not None:
            self.clarification_engine = clarification_engine
        else:
            self.clarification_engine = ClarificationEngine(provider=llm_provider)

    def process_message(
        self,
        conversation_id: str,
        user_message: str,
    ) -> ConversationTurnResult:
        """
        Execute one full conversation turn for a user message.

        Steps:
        1. Verify the conversation session exists.
        2. Handle empty input safely.
        3. Persist the incoming user message.
        4. Retrieve conversation history.
        5. Load the current WorkflowState from session.
        6. Extract structured facts via ExtractionService.
        7. Apply facts using the existing StateManager & Merger.
        8. Evaluate completeness via existing Validator.
        9. Ask a clarification question OR generate the final workflow.
        10. Persist the assistant response and updated state.
        11. Return the structured turn result.
        """
        # 1. Verify session exists
        session = self.db.get(ConversationSession, conversation_id)
        if session is None:
            raise ConversationNotFoundError(
                f"Conversation session '{conversation_id}' not found"
            )

        # 4. Load current workflow state
        if session.state_json and session.state_json.strip() and session.state_json != "{}":
            current_state = WorkflowState.model_validate_json(session.state_json)
        else:
            current_state = self.state_manager.create()

        # 2. Handle empty or blank user message safely
        cleaned_input = user_message.strip() if user_message else ""
        if not cleaned_input:
            clarification = self.clarification_engine.generate_question(current_state)
            assistant_text = f"I didn't receive any details. {clarification.question}"
            add_message(self.db, conversation_id, MessageRole.ASSISTANT, assistant_text)
            first_unresolved = next((a for a in current_state.ambiguities if not a.resolved), None)
            return ConversationTurnResult(
                conversation_id=conversation_id,
                assistant_message=assistant_text,
                status=current_state.status,
                workflow=None,
                missing_information=current_state.missing_mandatory_fields,
                ambiguity=first_unresolved,
                state=current_state,
            )

        # Retrieve history prior to this user turn
        history = get_messages(self.db, conversation_id)

        # 3. Persist user message
        t_user_persist_start = time.perf_counter()
        user_msg = add_message(
            db=self.db,
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=cleaned_input,
        )
        t_user_persist = time.perf_counter() - t_user_persist_start

        # 5 & 6. Call ExtractionService
        t_extract_start = time.perf_counter()
        try:
            patch = self.extraction_service.extract_patch(
                user_message=cleaned_input,
                conversation_history=history,
                current_state=current_state,
            )
            t_extract = time.perf_counter() - t_extract_start
        except LLMError as exc:
            t_extract = time.perf_counter() - t_extract_start
            logger.warning("LLM extraction failed: %s. Using deterministic fallback.", exc)
            t_clarify_start = time.perf_counter()
            clarification = self.clarification_engine.generate_question(current_state, history=history)
            t_clarify = time.perf_counter() - t_clarify_start
            assistant_text = (
                "I encountered an issue processing that message. "
                f"{clarification.question}"
            )
            t_persist_start = time.perf_counter()
            add_message(self.db, conversation_id, MessageRole.ASSISTANT, assistant_text)
            t_persist = time.perf_counter() - t_persist_start

            self.last_timings = {
                "gemini_extraction": t_extract,
                "state_merge": 0.0,
                "validation": 0.0,
                "gemini_clarification": t_clarify,
                "persistence": t_user_persist + t_persist,
                "user_persistence": t_user_persist,
                "assistant_persistence": t_persist,
                "retry_wait": 0.0,
            }

            first_unresolved = next((a for a in current_state.ambiguities if not a.resolved), None)
            return ConversationTurnResult(
                conversation_id=conversation_id,
                assistant_message=assistant_text,
                status=current_state.status,
                workflow=None,
                missing_information=current_state.missing_mandatory_fields,
                ambiguity=first_unresolved,
                state=current_state,
            )

        # 7. Apply patch using existing StateManager (which internally runs Validator)
        next_state = self.state_manager.apply(
            state=current_state,
            patch=patch,
            utterance_id=user_msg.id,
        )
        t_merge = getattr(self.state_manager, "last_merge_duration", 0.0)
        t_val = getattr(self.state_manager, "last_validation_duration", 0.0)

        # 8. Check completeness: if READY, generate workflow; if COLLECTING, ask clarification
        if next_state.status == ConversationStatus.READY:
            try:
                workflow_data = self.workflow_generator.generate_workflow(next_state)
                final_state = self.state_manager.mark_generated(next_state)
                assistant_text = self.workflow_generator.generate_confirmation_message(
                    final_state, workflow_data
                )
            except Exception as exc:
                logger.error("Workflow generation failed: %s", exc)
                # Keep state safe in READY
                workflow_data = None
                final_state = next_state
                assistant_text = (
                    "Your workflow information is complete, but an error occurred while "
                    "formatting the final representation. Please try again."
                )

            # Persist assistant response & state
            t_persist_start = time.perf_counter()
            add_message(self.db, conversation_id, MessageRole.ASSISTANT, assistant_text)
            session.state_json = final_state.model_dump_json()
            session.phase = final_state.status.value
            self.db.commit()
            self.db.refresh(session)
            t_persist = time.perf_counter() - t_persist_start

            self.last_timings = {
                "gemini_extraction": t_extract,
                "state_merge": t_merge,
                "validation": t_val,
                "gemini_clarification": 0.0,
                "persistence": t_user_persist + t_persist,
                "user_persistence": t_user_persist,
                "assistant_persistence": t_persist,
                "retry_wait": 0.0,
            }

            return ConversationTurnResult(
                conversation_id=conversation_id,
                assistant_message=assistant_text,
                status=final_state.status,
                workflow=workflow_data,
                missing_information=[],
                ambiguity=None,
                state=final_state,
            )

        # Status is COLLECTING
        t_clarify_start = time.perf_counter()
        clarification = self.clarification_engine.generate_question(
            state=next_state,
            history=history,
        )
        t_clarify = time.perf_counter() - t_clarify_start
        assistant_text = clarification.question

        # Persist assistant message & updated state
        t_persist_start = time.perf_counter()
        add_message(self.db, conversation_id, MessageRole.ASSISTANT, assistant_text)
        session.state_json = next_state.model_dump_json()
        session.phase = next_state.status.value
        self.db.commit()
        self.db.refresh(session)
        t_persist = time.perf_counter() - t_persist_start

        self.last_timings = {
            "gemini_extraction": t_extract,
            "state_merge": t_merge,
            "validation": t_val,
            "gemini_clarification": t_clarify,
            "persistence": t_user_persist + t_persist,
            "user_persistence": t_user_persist,
            "assistant_persistence": t_persist,
            "retry_wait": 0.0,
        }

        first_unresolved = next((a for a in next_state.ambiguities if not a.resolved), None)
        return ConversationTurnResult(
            conversation_id=conversation_id,
            assistant_message=assistant_text,
            status=next_state.status,
            workflow=None,
            missing_information=next_state.missing_mandatory_fields,
            ambiguity=first_unresolved,
            state=next_state,
        )
