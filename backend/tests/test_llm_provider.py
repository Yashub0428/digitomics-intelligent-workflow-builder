from unittest.mock import MagicMock
import pytest
from pydantic import BaseModel, ConfigDict

from app.config import Settings
from app.services.llm import (
    GeminiProvider,
    LLMAPIError,
    LLMConfigurationError,
    LLMMessage,
    LLMResponseValidationError,
    LLMTimeoutError,
    MockLLMProvider,
    get_llm_provider,
)


class SampleSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    count: int


def test_mock_provider_returns_valid_structured_output():
    mock = MockLLMProvider()
    expected = SampleSchema(name="item", count=42)
    mock.set_response(expected)

    result = mock.generate_structured(
        messages=[LLMMessage(role="user", content="hello")],
        response_schema=SampleSchema,
    )
    assert result.name == "item"
    assert result.count == 42
    assert mock.call_count == 1
    assert len(mock.last_messages) == 1
    assert mock.last_messages[0].content == "hello"


def test_mock_provider_queue_and_error():
    mock = MockLLMProvider()
    mock.enqueue_response({"name": "first", "count": 1})
    mock.enqueue_response(SampleSchema(name="second", count=2))

    res1 = mock.generate_structured([], SampleSchema)
    res2 = mock.generate_structured([], SampleSchema)

    assert res1.name == "first"
    assert res2.name == "second"

    # Set error
    mock.set_error(LLMAPIError("Upstream failure"))
    with pytest.raises(LLMAPIError, match="Upstream failure"):
        mock.generate_structured([], SampleSchema)


def test_mock_provider_raises_validation_error_on_invalid_data():
    mock = MockLLMProvider()
    # Invalid data: count must be an int, extra field forbidden
    mock.set_response({"name": "item", "count": "not_an_int", "extra": "not_allowed"})

    with pytest.raises(LLMResponseValidationError):
        mock.generate_structured([], SampleSchema)


def test_gemini_provider_missing_key_raises_configuration_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(LLMConfigurationError, match="Gemini API key is missing"):
        GeminiProvider(api_key="")


def test_gemini_provider_sanitizes_api_key_in_errors():
    provider = GeminiProvider(api_key="secret-api-key-12345", model="gemini-2.5-flash")
    raw_error = "Error connecting with key=secret-api-key-12345 and secret-api-key-12345"
    sanitized = provider._sanitize_error(raw_error)

    assert "secret-api-key-12345" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized or "[REDACTED]" in sanitized


def test_get_llm_provider_factory():
    # Test mock factory
    mock_settings = Settings(llm_provider="mock")
    provider = get_llm_provider(mock_settings)
    assert isinstance(provider, MockLLMProvider)

    # Test unknown provider
    bad_settings = Settings(llm_provider="unknown_vendor")
    with pytest.raises(LLMConfigurationError, match="Unsupported LLM provider"):
        get_llm_provider(bad_settings)


def test_gemini_provider_thinking_and_timeout_config():
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-3.5-flash",
        timeout_ms=12000,
        thinking_budget=0,
    )
    assert provider.timeout_ms == 12000
    assert provider.thinking_budget == 0


def test_gemini_provider_passes_options_to_generate_content():
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-3.5-flash",
        timeout_ms=15000,
        thinking_budget=0,
    )
    mock_resp = MagicMock()
    mock_resp.text = '{"name": "test", "count": 1}'
    mock_resp.parsed = None
    mock_resp.usage_metadata = None
    provider._client = MagicMock()
    provider._client.models.generate_content.return_value = mock_resp

    result = provider.generate_structured(
        messages=[LLMMessage(role="user", content="hi")],
        response_schema=SampleSchema,
    )
    assert result.name == "test"
    assert result.count == 1

    provider._client.models.generate_content.assert_called_once()
    _, kwargs = provider._client.models.generate_content.call_args
    config = kwargs["config"]
    assert config.thinking_config.thinking_budget == 0
    assert config.http_options.timeout == 15000
    assert config.automatic_function_calling.disable is True


def test_gemini_provider_maps_deadline_exceeded_to_timeout_error():
    from google.genai import errors

    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-3.5-flash",
        timeout_ms=15000,
    )
    provider._client = MagicMock()
    provider._client.models.generate_content.side_effect = errors.APIError(
        504, "Deadline expired before operation could complete"
    )

    with pytest.raises(LLMTimeoutError, match="timed out"):
        provider.generate_structured(
            messages=[LLMMessage(role="user", content="hi")],
            response_schema=SampleSchema,
        )
