class LLMError(Exception):
    """Base exception for all LLM-related errors."""


class LLMConfigurationError(LLMError):
    """Raised when an LLM provider is misconfigured (e.g. missing credentials or model)."""


class LLMAuthenticationError(LLMError):
    """Raised when authentication with the LLM provider fails."""


class LLMAPIError(LLMError):
    """Raised when the LLM provider returns an API error or network failure."""


class LLMTimeoutError(LLMError):
    """Raised when an LLM request exceeds its time limit."""


class LLMResponseValidationError(LLMError):
    """Raised when the structured output returned by the LLM violates the expected Pydantic schema."""
