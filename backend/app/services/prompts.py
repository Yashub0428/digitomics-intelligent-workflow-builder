import json
from typing import Any

from app.schemas.workflow import WorkflowState
from app.services.llm.base import LLMMessage

EXTRACTION_SYSTEM_PROMPT = """You are a precision Information Extraction Agent for an automation workflow builder.
Your sole responsibility is to extract explicitly stated facts from the user's message into a structured WorkflowStatePatch.
You are NOT the state manager, NOT an executor, and NOT a conversational chatbot.
You must NEVER directly modify global application state. You only emit structured patches.

=== CRITICAL ANTI-ASSUMPTION RULES (MOST IMPORTANT) ===
1. NEVER invent, assume, default, or hallucinate information not explicitly stated by the user.
2. Do NOT assume common platforms or vendors (e.g. do NOT assume Gmail, Slack, Stripe, AWS, Jira unless explicitly stated).
3. Do NOT assume recipients, email addresses, phone numbers, or channel names.
4. Do NOT assume schedules, intervals, frequencies, or timezones.
5. Do NOT assume conditions or filters.
6. Do NOT assume action parameters (e.g. do not invent email subject, email body, URL, or payload).
7. If an action naturally requires delivery/notification targets (e.g. email, Slack, chat notification):
   - Set `action.needs_recipients = true` on the Action.
   - List expected parameter keys in `action.required_parameters` (e.g. ["subject", "body"] for an email).
   - Only populate parameters and recipients that the user EXPLICITLY stated. Leave missing items unpopulated so deterministic validation can catch them.

=== AMBIGUITY HANDLING ===
If the user's request is ambiguous with multiple realistic interpretations (e.g. "Notify the team" - could be Slack, Email, Teams):
- Do NOT pick an arbitrary option.
- Create an Ambiguity object in `ambiguities`:
  - `id`: unique string like "amb_notify_channel"
  - `path`: field path being clarified (e.g. "actions.0.kind")
  - `question`: clear clarification question
  - `options`: list of AmbiguityOption(id=..., label=...)
  - `resolved`: false
If the user is answering a prior ambiguity, populate `resolve_ambiguities` with `AmbiguityResolution(ambiguity_id=..., chosen=...)` and set the corresponding field.

=== MULTIPLE FACTS & CORRECTIONS ===
- If the user provides multiple facts in one message, extract ALL of them into the patch.
- If the user corrects or changes a previous answer (e.g. "Actually, use Outlook instead of Gmail"), extract the new value.
- If the user sends a greeting or irrelevant text (e.g. "hi", "how are you"), return an empty patch.
"""


def build_extraction_messages(
    user_message: str,
    conversation_history: list[dict[str, Any]] | None = None,
    current_state: WorkflowState | None = None,
) -> list[LLMMessage]:
    """
    Construct the message sequence for structured information extraction.
    Includes context from past conversation and currently collected slots.
    """
    messages: list[LLMMessage] = []

    # Summarize current state context if available
    context_lines = []
    if current_state:
        collected_summary = {
            path: item.value for path, item in current_state.collected.items()
        }
        context_lines.append(f"Current State Status: {current_state.status.value}")
        context_lines.append(f"Currently Collected Slots: {json.dumps(collected_summary)}")
        if current_state.missing_mandatory_fields:
            missing_paths = [m.path for m in current_state.missing_mandatory_fields]
            context_lines.append(f"Currently Missing Fields: {json.dumps(missing_paths)}")
        unresolved_ambs = [a.id for a in current_state.ambiguities if not a.resolved]
        if unresolved_ambs:
            context_lines.append(f"Unresolved Ambiguities: {json.dumps(unresolved_ambs)}")

    context_str = "\n".join(context_lines)

    # Add historical conversation context
    if conversation_history:
        for turn in conversation_history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            messages.append(LLMMessage(role=role, content=content))

    # Current user turn with context preface if needed
    current_turn_content = user_message
    if context_str:
        current_turn_content = f"[WORKFLOW CONTEXT]\n{context_str}\n\n[USER MESSAGE]\n{user_message}"

    messages.append(LLMMessage(role="user", content=current_turn_content))
    return messages


CLARIFICATION_SYSTEM_PROMPT = """You are a polite, focused Clarification Assistant for an automation workflow builder.
Your task is to generate ONE friendly, human-sounding clarification question targeting the single most important missing or ambiguous piece of workflow information.

=== GUIDELINES ===
1. Ask ONE clear, focused question.
2. NEVER mention code or schema paths like "trigger.kind", "actions.0.parameters.sheet", or "trigger_source".
3. Speak naturally (e.g. "Which spreadsheet should new rows be added to?" instead of "actions.0.parameters.sheet is required").
4. If options are provided (such as when resolving an ambiguity), present the options conversationally.
5. Provide a helpful 'reason' explaining why this detail is needed for the automation.
6. Strictly return a structured ClarificationQuestion object.
"""


def build_clarification_messages(
    state: WorkflowState,
    target_field: str,
    reason: str,
    options: list[str] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> list[LLMMessage]:
    """Build input messages for the LLM clarification question generator."""
    summary_parts = []
    if state.intent.summary:
        summary_parts.append(f"Workflow Intent: {state.intent.summary}")
    if state.trigger.kind:
        summary_parts.append(f"Trigger: {state.trigger.kind}")
    if state.actions:
        action_names = [a.kind or "action" for a in state.actions]
        summary_parts.append(f"Actions: {', '.join(action_names)}")

    context_prompt = (
        f"Workflow Summary:\n"
        f"{chr(10).join(summary_parts) if summary_parts else 'New workflow in progress.'}\n\n"
        f"Next Missing/Ambiguous Field to Clarify: {target_field}\n"
        f"Reason Needed: {reason}\n"
    )
    if options:
        context_prompt += f"Available Options: {', '.join(options)}\n"

    context_prompt += (
        "\nGenerate a natural, polite clarification question for the user to collect this information."
    )

    return [LLMMessage(role="user", content=context_prompt)]

