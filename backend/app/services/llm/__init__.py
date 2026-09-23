from app.config import Settings, get_settings
from app.services.llm.base import LLMMessage, LLMProvider
from app.services.llm.exceptions import (
    LLMAPIError,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMError,
    LLMResponseValidationError,
    LLMTimeoutError,
)
from app.services.llm.gemini import GeminiProvider
from app.services.llm.mock import MockLLMProvider


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Factory to instantiate the configured LLMProvider."""
    cfg = settings or get_settings()
    provider_name = (cfg.llm_provider or "").lower().strip()

    if provider_name == "gemini":
        return GeminiProvider(
            api_key=cfg.gemini_api_key,
            model=cfg.llm_model,
            timeout_ms=cfg.llm_timeout_ms,
            thinking_budget=cfg.llm_thinking_budget,
        )
    if provider_name == "mock":
        return MockLLMProvider()

    raise LLMConfigurationError(
        f"Unsupported LLM provider '{cfg.llm_provider}'. Supported providers are: 'gemini', 'mock'."
    )


__all__ = [
    "GeminiProvider",
    "LLMAPIError",
    "LLMAuthenticationError",
    "LLMConfigurationError",
    "LLMError",
    "LLMMessage",
    "LLMProvider",
    "LLMResponseValidationError",
    "LLMTimeoutError",
    "MockLLMProvider",
    "get_llm_provider",
]
