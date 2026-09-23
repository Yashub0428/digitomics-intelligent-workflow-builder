# Intelligent Conversational Workflow Builder

An LLM-powered conversational assistant that converts natural-language automation requests into validated, structured workflows through information extraction, ambiguity detection, targeted clarification, deterministic state management, and final workflow specification generation.

---

## Overview

Non-technical and technical users frequently want to automate workflows but struggle to articulate all necessary parameters upfront:
- **Natural-Language Input**: Users describe their desired automation in free-form natural language (e.g., *"When I receive an invoice, notify the finance team"*).
- **Structured Extraction**: The system extracts known triggers, sources, actions, and recipients into structured data rather than free-form text.
- **Ambiguity & Gap Detection**: The engine identifies missing mandatory fields (such as notification channels or target addresses) and inherent ambiguities.
- **Targeted Clarification**: It asks focused, one-question-at-a-time clarification prompts to collect only what is strictly missing.
- **Multi-Turn State Management**: A canonical workflow state is maintained, tracked, and updated deterministically across conversational turns.
- **Guaranteed Completeness**: A structured workflow specification is generated **only** when all required information is resolved and validated.
- **Scope Boundary**: Workflow execution engines and third-party API execution integrations are intentionally out of scope for this architecture; the focus is on robust, reliable conversational synthesis of executable workflow definitions.

---

## Key Features

- **Natural-Language Workflow Understanding**: Interprets intent, triggers, sources, filters, actions, schedules, and recipients from conversational dialogue.
- **Structured LLM Extraction**: Generates strictly validated `WorkflowStatePatch` payloads using schema-constrained JSON output.
- **Pydantic Validation**: Strong compile-time and runtime type validation across state schemas, API envelopes, and extraction payloads.
- **Deterministic State Management**: Predictable state transitions and path-based merging; the LLM is never permitted to mutate application state directly.
- **Intelligent Clarification Engine**: Produces context-aware clarification questions addressing missing fields and ambiguous alternatives.
- **Ambiguity Handling**: Detects and resolves choices (e.g., Email vs. Slack vs. Teams) before declaring readiness.
- **Conversation Persistence**: SQLite database storing sessions and message histories with ACID guarantees.
- **FastAPI REST API**: Comprehensive, typed REST endpoints with CORS support, structured error handlers, and `/api` + `/api/v1` route aliasing.
- **React + TypeScript Frontend**: Responsive, modern user interface built with Tailwind CSS, supporting interactive multi-turn dialogue.
- **Interactive React Flow Visualization**: Read-only, auto-laid-out graphical representation of triggers, conditions, actions, and recipients.
- **Dual Visual / JSON Workflow Views**: Inspect the synthesized workflow graphically or view/copy formatted raw JSON with download support.
- **Mock LLM Provider**: Deterministic, zero-dependency provider for instant automated testing and continuous integration.
- **Gemini LLM Provider**: Real Google Gemini integration with strict response schemas, reasoning suppression, and client timeouts.
- **Deterministic Clarification Fallback**: Rule-based fallback ensures dialogue never crashes if the LLM provider experiences network latency or outages.
- **Comprehensive Automated Tests**: 84 backend pytest tests and 19 frontend Vitest tests covering edge cases, state transitions, and UI components.

---

## Architecture

```text
User
  ↓
React Frontend (Vite + TypeScript + Tailwind CSS)
  ↓ [HTTP REST API]
FastAPI REST API
  ↓
Conversation Orchestrator
  ├── Message Persistence  (SQLite / SQLAlchemy)
  ├── LLM Extraction        (Gemini Provider / Mock Provider)
  ├── State Merger          (Path-based deterministic merge engine)
  ├── State Validator       (Completeness & ambiguity rule engine)
  ├── Clarification Engine  (LLM-guided with deterministic fallback)
  └── Workflow Generator    (Validated state → Final JSON specification)
  ↓
Structured Workflow
  ↓
React Flow Visualization  (Read-only visual DAG)
```

### Core Architectural Principle

> **The LLM is responsible for language understanding and structured extraction, while deterministic backend components remain the sole source of truth for state, validation, readiness, and workflow generation.**

The LLM never directly mutates application state. Instead, it extracts an incremental patch (`WorkflowStatePatch`). The backend's `WorkflowMerger` deterministically validates and applies the patch, and the `WorkflowValidator` strictly determines whether the workflow is complete (`READY`) or requires further dialogue (`COLLECTING`).

---

## Backend Structure

```text
backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── conversations.py    # Conversation & message endpoints
│   │   │   └── health.py           # Health check endpoints
│   │   └── exception_handlers.py   # Global error formatting
│   ├── db/
│   │   ├── models.py               # SQLAlchemy ConversationSession & Message models
│   │   └── session.py              # Engine, sessionmaker, and table initialization
│   ├── schemas/
│   │   ├── clarification.py        # Clarification question schema
│   │   ├── conversation.py         # Request/response API schemas
│   │   ├── errors.py               # Standardized error responses
│   │   ├── health.py               # Health check status schema
│   │   ├── message.py              # Message payloads & roles
│   │   ├── orchestrator.py         # Turn result envelopes
│   │   └── workflow.py             # Canonical WorkflowState & WorkflowStatePatch models
│   ├── services/
│   │   ├── llm/
│   │   │   ├── base.py             # BaseLLMProvider abstract interface
│   │   │   ├── exceptions.py       # Custom LLM exception types
│   │   │   ├── gemini.py           # Google Gemini provider with ThinkingConfig & HttpOptions
│   │   │   └── mock.py             # Deterministic MockLLMProvider for tests
│   │   ├── clarification.py        # Clarification generation & fallback logic
│   │   ├── extraction.py           # Prompting & schema extraction
│   │   ├── merger.py               # Path-based deterministic state merge engine
│   │   ├── message_service.py      # Message persistence service
│   │   ├── orchestrator.py         # Multi-step conversational turn pipeline
│   │   ├── prompts.py              # System prompts & anti-assumption extraction rules
│   │   ├── state_manager.py        # Canonical state initialization & transitions
│   │   ├── validator.py            # Completeness & mandatory field validation rules
│   │   └── workflow_generator.py   # Transformation of READY state into final JSON
│   ├── config.py                   # Pydantic Settings & environment variables
│   └── main.py                     # FastAPI application factory & lifespan
├── tests/
│   ├── test_api_conversations.py   # End-to-end REST API endpoint tests
│   ├── test_extraction.py          # Structured extraction unit tests
│   ├── test_llm_provider.py        # Gemini and Mock provider tests
│   ├── test_merger.py              # State merger & path updating tests
│   ├── test_message_service.py     # Message persistence tests
│   ├── test_orchestrator.py        # Orchestration pipeline & fallback tests
│   ├── test_state_manager.py       # State manager unit tests
│   └── test_validator.py           # Validation rules & completeness tests
├── .env.example
├── pytest.ini
└── requirements.txt
```

### Major Service Responsibilities

- **`ConversationOrchestrator`**: Coordinates each conversational turn: persists user utterance $\to$ invokes extraction $\to$ executes state merge $\to$ runs validation $\to$ triggers clarification (or final workflow generation) $\to$ persists assistant reply.
- **`ExtractionService`**: Submits user utterances with context to the LLM and parses the response strictly against `WorkflowStatePatch`.
- **`WorkflowMerger`**: Applies the state patch using dotted-path assignments, array merges, and removals without overwriting unmentioned fields.
- **`WorkflowValidator`**: Evaluates completeness rules (e.g., triggers need kinds/sources, actions need kinds/parameters, actions needing recipients require recipient entries) and checks for unresolved ambiguities.
- **`ClarificationEngine`**: Generates context-aware clarification questions addressing missing fields; automatically uses a deterministic template if the LLM is unavailable.
- **`WorkflowGenerator`**: Converts a validated `READY` state into the final standardized workflow representation.
- **`MessageService`**: Manages thread history in SQLite to feed conversation context into turns.

---

## Frontend

The frontend is built with **React 19**, **TypeScript**, and **Tailwind CSS v4** via **Vite**:

- **Chat Interface**: Streamlined message dialogue with real-time assistant responses, loading indicators, and error banners.
- **Conversation State**: Manages active conversation IDs and message history synchronized with the REST API.
- **Workflow State Panel**: Live sidebar displaying current workflow status (`COLLECTING` vs. `READY` / `GENERATED`), intent summary, detected trigger, and configured actions.
- **Workflow Generation Modal**: Accessible when the workflow reaches completion, featuring:
  - **Visual Tab**: Interactive graph rendered with `@xyflow/react`.
  - **JSON Tab**: Formatted syntax view with **Copy to Clipboard** and **Download JSON** capabilities.
- **React Flow Visualization**: A read-only graph mapping:
  $$\text{Trigger} \longrightarrow \text{Condition (if any)} \longrightarrow \text{Action(s)} \longrightarrow \text{Recipient(s)}$$
  Custom node components (`TriggerNode`, `ConditionNode`, `ActionNode`, `RecipientNode`) display relevant metadata with directional smoothstep edges.

---

## Conversation Flow

Here is a typical multi-turn flow:

```text
User:
"Whenever I receive an invoice, notify the finance team."

Assistant:
"What email inbox should I monitor?"

User:
"Gmail inbox."

Assistant:
"How should the finance team be notified?"

User:
"Email."

Assistant:
"What email address should receive the notification?"

User:
"finance@company.com"

Assistant:
"Your workflow for 'Notify finance team when an invoice is received' is complete and validated with 1 action and 1 recipient."
```

The backend **only** generates the final workflow specification once all mandatory fields are gathered and ambiguities are resolved. Until then, the state remains `COLLECTING` and targeted clarification questions are returned.

---

## Example Generated Workflow

Below is a representative output produced by `WorkflowGenerator`:

```json
{
  "id": "wf_a1b2c3d4e5",
  "name": "Notify finance team when an invoice is received",
  "status": "ready",
  "schema_version": 1,
  "intent": {
    "summary": "Notify finance team when an invoice is received",
    "tags": ["invoice", "notification"]
  },
  "trigger": {
    "kind": "receive_invoice",
    "parameters": {},
    "source": {
      "kind": "gmail",
      "identifier": "inbox"
    }
  },
  "conditions": [],
  "actions": [
    {
      "id": "action_notify_finance",
      "kind": "email",
      "parameters": {
        "message": "Please review the new invoice and process it accordingly."
      },
      "needs_recipients": true
    }
  ],
  "recipients": [
    {
      "channel": "email",
      "address": "finance@company.com",
      "target_identifier": "finance_team"
    }
  ],
  "preferences": {}
}
```

---

## LLM Design

- **Real Provider**: Integrates Google Gemini Developer API using the official `google-genai` SDK.
- **Default Model**: **`gemini-3-flash-preview`** (selected for active availability, speed, and schema compliance).
- **Structured JSON Schema**: Prompts utilize `response_mime_type="application/json"` with JSON schemas generated directly from Pydantic models.
- **Predictable Latency**:
  - `thinking_budget=0` suppresses unnecessary chain-of-thought tokens on reasoning models for simple extraction tasks.
  - `timeout=15000` (15s deadline) enforces timely HTTP execution.
  - Live turn latency measured at **~6.4s** total (~4.1s extraction, ~2.1s clarification).
- **Function Calling**: `automatic_function_calling=False` prevents unexpected external tool calls.
- **Deterministic Mock Provider**: `MockLLMProvider` queues deterministic responses for test runs without requiring network calls or API keys.
- **Fail-Safe Fallbacks**: If Gemini experiences network timeouts, quota limits, or outages, `ClarificationEngine` automatically falls back to deterministic rule-based questions without crashing.
- **Key Redaction**: API keys are excluded from logging, error strings, and exception traces.

> [!CAUTION]
> Never commit `.env` or hard-code API keys. API keys should only be supplied via local environment variables.

---

## API Endpoints

The API is mounted with both `/api` and versioned `/api/v1` prefixes.

### Conversations & Messages

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/conversations` | Create a new conversation session with an empty `WorkflowState`. |
| `POST` | `/api/conversations/{conversation_id}/messages` | Post a user utterance; runs orchestrator turn and returns assistant response. |
| `GET` | `/api/conversations/{conversation_id}/messages` | Retrieve full message history for the conversation. |
| `GET` | `/api/conversations/{conversation_id}/state` | Retrieve current canonical `WorkflowState` (including status, collected fields, ambiguities). |
| `GET` | `/api/conversations/{conversation_id}/workflow` | Retrieve final `GeneratedWorkflow` specification. (Returns HTTP 400 if state is still `COLLECTING`). |
| `GET` | `/api/health` | Health check and system status. |

*(All `/api/...` routes are additionally accessible via `/api/v1/...`)*

---

## Setup & Running

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Windows PowerShell (or bash / zsh)

---

### Backend Setup

1. **Navigate to the backend directory and create a virtual environment**:
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   *(On macOS/Linux: `source .venv/bin/activate`)*

2. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   ```powershell
   Copy-Item .env.example .env
   ```
   Edit `.env` to configure your provider:
   ```env
   APP_NAME=digitomics-workflow-builder
   APP_ENV=development
   DEBUG=false
   DATABASE_URL=sqlite:///./app.db
   LLM_PROVIDER=gemini
   LLM_MODEL=gemini-3-flash-preview
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```
   *(If you do not have a Gemini API key, leave `LLM_PROVIDER=mock` or configure `GEMINI_API_KEY=""`; the system will run with deterministic fallback).*

4. **Start the FastAPI server**:
   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```
   The backend will be available at `http://127.0.0.1:8000` with interactive API docs at `http://127.0.0.1:8000/docs`.

---

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```powershell
   cd ..\frontend
   ```

2. **Install Node dependencies**:
   ```powershell
   npm install
   ```

3. **Configure environment variables**:
   ```powershell
   Copy-Item .env.example .env
   ```
   Ensure `.env` contains:
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   ```

4. **Start the Vite development server**:
   ```powershell
   npm run dev
   ```
   The application will be accessible at `http://127.0.0.1:5173`.

---

## Testing

All test suites run completely offline and use the mocked LLM provider by default.

### Backend Tests (pytest)
```powershell
cd backend
.\.venv\Scripts\pytest
```
- **Status**: **84 passed** in ~2.4s
- Validates:
  - API endpoints, status codes, and error envelopes
  - Path-based state merger
  - Mandatory field validation & ambiguity checks
  - Message persistence in SQLite
  - Extraction service & prompt schema compliance
  - Orchestrator multi-turn state accumulation
  - LLM provider timeout handling and fallback triggers

### Frontend Tests (Vitest)
```powershell
cd frontend
npm test
```
- **Status**: **19 passed** in ~3.0s
- Validates:
  - React Flow layout engine (`workflowToGraph`)
  - Linear single-action graph generation
  - Multi-action and recipient branching
  - Edge connectivity and node styling
  - Message rendering and tab switching (Visual vs. JSON)

### Frontend Production Build
```powershell
cd frontend
npm run build
```
- **Status**: Clean production build with 0 TypeScript / bundling errors.

---

## Design Decisions

1. **LLM + Deterministic Backend**: Keeps business logic, state mutation, and readiness gates deterministic and reproducible. The LLM parses natural language into facts; code decides if the workflow is complete.
2. **Structured Output over Free-Form Parsing**: Uses native Gemini JSON schemas and Pydantic models. Avoids fragile regex parsing or unvalidated JSON code blocks.
3. **Pydantic Validation**: Strict schemas (`extra="forbid"`) protect the state from hallucinated fields or invalid nested objects.
4. **Orchestrator Pattern**: Centralizes turn lifecycle into a single pipeline, decoupling API routes from domain logic.
5. **Deterministic Clarification Fallback**: Ensures system resilience; if an LLM call exceeds 15 seconds or hits rate limits, the user receives an immediate template-based clarification question instead of a 500 error.
6. **Separation of Extraction, State Management, Validation, Clarification, and Generation**: Each step has a single, well-tested responsibility with minimal coupling.
7. **Mock Provider for Reliable CI/CD**: Tests run in seconds without external network dependencies, rate limits, or API costs.
8. **Read-Only Workflow Visualization**: React Flow is utilized purely to render the canonical generated state. This prevents UI-state divergence and keeps the backend as the single source of truth.

---

## Limitations

- **No Workflow Execution**: This system builds and validates workflow specifications; executing triggers, monitoring webhooks, or making third-party API calls is out of scope.
- **No External Integrations**: Gmail, Slack, and webhook integrations are represented as structured metadata specifications rather than live OAuth connections.
- **Read-Only Visualization**: The graph view renders the synthesized workflow; manual drag-and-drop node editing is intentionally omitted in favor of conversational iteration.
- **Defined Workflow Domain**: Designed around the assignment's structured automation schema (triggers, sources, conditions, actions, recipients, schedules).

---

## Future Improvements

- **Expanded Triggers & Actions**: Additional pre-built templates for webhooks, cron expressions, multi-service connectors, and data transformations.
- **Complex Conditional Branching**: Support for multi-branch `if/then/else` decision trees in the visualizer and schema.
- **Bi-Directional Workflow Editing**: Allowing users to edit parameters directly in the diagram and feeding edits back into conversation state.
- **Multi-Provider LLM Support**: Expand providers beyond Gemini to include Anthropic Claude and OpenAI.
- **Streaming Responses**: Server-Sent Events (SSE) for token-by-token assistant streaming during clarification turns.
- **Multi-Tenant Authentication**: User authentication, workspace partitioning, and conversation persistence per tenant.
- **Persistent Production Storage**: Migration from SQLite to PostgreSQL with Alembic migrations.
- **Observability & OpenTelemetry**: Distributed tracing across LLM extraction, validation passes, and API durations.

---

## Project Structure

```text
digitomics-workflow-builder/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── db/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── config.py
│   │   └── main.py
│   ├── tests/
│   ├── .env.example
│   ├── pytest.ini
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   │   ├── Chat/
│   │   │   ├── Workflow/
│   │   │   └── common/
│   │   ├── test/
│   │   ├── types/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── .env.example
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── .gitignore
└── README.md
```

---

## Submission

- **GitHub Repository**: [https://github.com/Yashub0428/digitomics-intelligent-workflow-builder](https://github.com/Yashub0428/digitomics-intelligent-workflow-builder)

This repository contains the complete source code, test suites, configuration examples, and documentation for both backend and frontend.
