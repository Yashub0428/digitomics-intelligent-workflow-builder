from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T", bound=BaseModel)


class LLMMessage(BaseModel):
    """Standard message representation for conversation turns sent to LLMs."""

    model_config = ConfigDict(extra="forbid")

    role: str
    content: str


class LLMProvider(ABC):
    """Abstract interface for LLM providers supporting structured generation."""

    @abstractmethod
    def generate_structured(
        self,
        messages: list[LLMMessage] | list[dict[str, str]],
        response_schema: type[T],
        system_instruction: str | None = None,
    ) -> T:
        """
        Generate a structured response adhering strictly to response_schema.

        Args:
            messages: List of conversation messages (LLMMessage or dict with 'role' and 'content').
            response_schema: The target Pydantic model class.
            system_instruction: Optional system instruction guiding model behavior.

        Returns:
            An instance of response_schema.

        Raises:
            LLMResponseValidationError: If the model's output cannot be parsed into response_schema.
            LLMAuthenticationError: On authentication/credential issues.
            LLMConfigurationError: On provider configuration issues.
            LLMTimeoutError: On request timeout.
            LLMAPIError: On other upstream API failures.
        """
        raise NotImplementedError
