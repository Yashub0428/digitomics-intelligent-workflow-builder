import json
import logging
import os
import re
import time
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.services.llm.base import LLMMessage, LLMProvider
from app.services.llm.exceptions import (
    LLMAPIError,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMResponseValidationError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    """
    LLM provider utilizing the official Google GenAI Python SDK.
    Enforces structured responses adhering to Pydantic schemas.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_ms: int | None = None,
        thinking_budget: int | None = None,
    ) -> None:
        self.last_call_timings: dict[str, Any] = {}
        settings = get_settings()
        resolved_key = api_key if api_key is not None else (settings.gemini_api_key or os.environ.get("GEMINI_API_KEY"))

        if not resolved_key or not resolved_key.strip():
            raise LLMConfigurationError(
                "Gemini API key is missing. Configure GEMINI_API_KEY in environment or .env."
            )

        self._api_key = resolved_key.strip()
        self.model = model or settings.llm_model or os.environ.get("LLM_MODEL") or "gemini-3-flash-preview"
        self.timeout_ms = timeout_ms if timeout_ms is not None else getattr(settings, "llm_timeout_ms", 15000)
        self.thinking_budget = thinking_budget if thinking_budget is not None else getattr(settings, "llm_thinking_budget", 0)

        try:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
        except Exception as exc:
            sanitized = self._sanitize_error(str(exc))
            raise LLMConfigurationError(f"Failed to initialize Gemini client: {sanitized}") from exc

    def _sanitize_error(self, message: str) -> str:
        """Strip API key or sensitive patterns from error messages before exposure."""
        sanitized = message.replace(self._api_key, "[REDACTED_API_KEY]")
        sanitized = re.sub(r"key=[A-Za-z0-9_\-]+", "key=[REDACTED]", sanitized)
        return sanitized

    def _format_contents(
        self,
        messages: list[LLMMessage] | list[dict[str, str]],
    ) -> list[Any]:
        """Convert input messages into google.genai types.Content objects."""
        from google.genai import types

        contents: list[types.Content] = []
        for msg in messages:
            if isinstance(msg, LLMMessage):
                role = msg.role
                content = msg.content
            else:
                role = msg.get("role", "user")
                content = msg.get("content", "")

            # Map chat roles: Gemini uses 'user' and 'model'
            gemini_role = "model" if role in ("assistant", "model") else "user"
            contents.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part.from_text(text=content)],
                )
            )
        return contents

    def generate_structured(
        self,
        messages: list[LLMMessage] | list[dict[str, str]],
        response_schema: type[T],
        system_instruction: str | None = None,
    ) -> T:
        """Generate a structured response parsed directly into the given Pydantic schema."""
        from google.genai import errors, types

        contents = self._format_contents(messages)

        # Developer API compatibility: use response_json_schema from Pydantic model
        if hasattr(response_schema, "model_json_schema"):
            schema_arg: dict[str, Any] = {
                "response_mime_type": "application/json",
                "response_json_schema": response_schema.model_json_schema(),
            }
        else:
            schema_arg = {
                "response_mime_type": "application/json",
                "response_schema": response_schema,
            }

        config_kwargs: dict[str, Any] = {
            **schema_arg,
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
            "system_instruction": system_instruction,
            "temperature": 0.0,
        }

        if self.timeout_ms is not None and self.timeout_ms > 0:
            config_kwargs["http_options"] = types.HttpOptions(timeout=self.timeout_ms)

        if self.thinking_budget is not None:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=self.thinking_budget)

        config = types.GenerateContentConfig(**config_kwargs)

        t_call_start = time.perf_counter()
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
        except errors.APIError as exc:
            sanitized = self._sanitize_error(str(exc))
            if exc.code in (401, 403):
                raise LLMAuthenticationError(f"Gemini authentication failed: {sanitized}") from exc
            if exc.code in (408, 504) or "timeout" in sanitized.lower() or "deadline" in sanitized.lower():
                raise LLMTimeoutError(f"Gemini request timed out: {sanitized}") from exc
            raise LLMAPIError(f"Gemini API error (HTTP {exc.code}): {sanitized}") from exc
        except TimeoutError as exc:
            raise LLMTimeoutError("Gemini request timed out") from exc
        except Exception as exc:
            sanitized = self._sanitize_error(str(exc))
            if "timeout" in sanitized.lower() or "deadline" in sanitized.lower():
                raise LLMTimeoutError(f"Gemini request timed out: {sanitized}") from exc
            raise LLMAPIError(f"Gemini request failed: {sanitized}") from exc
        finally:
            call_duration = time.perf_counter() - t_call_start

        # Record usage metrics
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
        thoughts_tokens = getattr(usage, "thoughts_token_count", 0) if usage else 0
        candidates_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0
        total_tokens = getattr(usage, "total_token_count", 0) if usage else 0

        self.last_call_timings = {
            "duration": call_duration,
            "prompt_tokens": prompt_tokens,
            "thoughts_tokens": thoughts_tokens,
            "candidates_tokens": candidates_tokens,
            "total_tokens": total_tokens,
            "retry_wait": 0.0,
            "retries": 0,
        }
        logger.info(
            "Gemini API call finished in %.2fs [prompt_tokens=%s, thoughts_tokens=%s, candidates_tokens=%s, total_tokens=%s]",
            call_duration, prompt_tokens, thoughts_tokens, candidates_tokens, total_tokens,
        )

        # Extract structured output
        raw_text = getattr(response, "text", None)
        parsed = getattr(response, "parsed", None)

        if parsed is not None and isinstance(parsed, response_schema):
            return parsed

        if parsed is not None and isinstance(parsed, (dict, BaseModel)):
            try:
                if isinstance(parsed, BaseModel):
                    return response_schema.model_validate(parsed.model_dump())
                return response_schema.model_validate(parsed)
            except ValidationError as exc:
                raise LLMResponseValidationError(
                    f"Parsed Gemini output failed validation against {response_schema.__name__}: {exc}"
                ) from exc

        if not raw_text or not raw_text.strip():
            raise LLMResponseValidationError("Gemini returned an empty response")

        try:
            return response_schema.model_validate_json(raw_text)
        except (ValidationError, json.JSONDecodeError) as exc:
            raise LLMResponseValidationError(
                f"Failed to parse Gemini response into {response_schema.__name__}: {exc}"
            ) from exc
