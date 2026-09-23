import json
from collections import deque
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.services.llm.base import LLMMessage, LLMProvider
from app.services.llm.exceptions import LLMAPIError, LLMResponseValidationError

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    """
    Mock LLM provider for testing without calling external APIs.

    Supports queueing deterministic structured responses, custom errors,
    and inspecting invocation history.
    """

    def __init__(self, default_response: BaseModel | dict[str, Any] | str | None = None) -> None:
        self._default_response = default_response
        self._response_queue: deque[BaseModel | dict[str, Any] | str] = deque()
        self._pending_error: Exception | None = None
        self.call_count: int = 0
        self.last_messages: list[LLMMessage] = []
        self.last_response_schema: type[BaseModel] | None = None
        self.last_system_instruction: str | None = None
        self.history: list[dict[str, Any]] = []

    def set_response(self, response: BaseModel | dict[str, Any] | str) -> None:
        """Set a single response that will be returned for calls (or clears queue and sets default)."""
        self._default_response = response
        self._response_queue.clear()
        self._pending_error = None

    def enqueue_response(self, response: BaseModel | dict[str, Any] | str) -> None:
        """Queue a response to be returned on the next sequential call."""
        self._response_queue.append(response)

    def set_error(self, error: Exception) -> None:
        """Configure an exception to be raised on the next call."""
        self._pending_error = error

    def clear(self) -> None:
        """Reset mock state, queues, and call history."""
        self._default_response = None
        self._response_queue.clear()
        self._pending_error = None
        self.call_count = 0
        self.last_messages.clear()
        self.last_response_schema = None
        self.last_system_instruction = None
        self.history.clear()

    def generate_structured(
        self,
        messages: list[LLMMessage] | list[dict[str, str]],
        response_schema: type[T],
        system_instruction: str | None = None,
    ) -> T:
        self.call_count += 1
        normalized_messages = [
            m if isinstance(m, LLMMessage) else LLMMessage.model_validate(m)
            for m in messages
        ]
        self.last_messages = normalized_messages
        self.last_response_schema = response_schema
        self.last_system_instruction = system_instruction
        self.history.append({
            "messages": normalized_messages,
            "response_schema": response_schema,
            "system_instruction": system_instruction,
        })

        if self._pending_error is not None:
            err = self._pending_error
            self._pending_error = None
            raise err

        if self._response_queue:
            raw = self._response_queue.popleft()
        elif self._default_response is not None:
            raw = self._default_response
        else:
            raise LLMAPIError("MockLLMProvider: No response has been configured or queued.")

        try:
            if isinstance(raw, response_schema):
                return raw
            if isinstance(raw, BaseModel):
                return response_schema.model_validate(raw.model_dump())
            if isinstance(raw, dict):
                return response_schema.model_validate(raw)
            if isinstance(raw, str):
                return response_schema.model_validate_json(raw)
            raise LLMResponseValidationError(
                f"MockLLMProvider: Unsupported response payload type '{type(raw).__name__}'"
            )
        except (ValidationError, json.JSONDecodeError) as exc:
            raise LLMResponseValidationError(
                f"MockLLMProvider: Failed to parse response into {response_schema.__name__}: {exc}"
            ) from exc
