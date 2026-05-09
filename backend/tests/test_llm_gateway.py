from unittest.mock import MagicMock, patch

import pytest

from app.services.llm_gateway import CacheBreakpoint, LLMGateway, Message
from app.services.llm_models import TIER_MODEL_MAP


def _make_mock_response(
    text: str = "ok",
    input_tokens: int = 100,
    output_tokens: int = 50,
    cache_creation: int = 0,
    cache_read: int = 0,
) -> MagicMock:
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    response.stop_reason = "end_turn"
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    response.usage.cache_creation_input_tokens = cache_creation
    response.usage.cache_read_input_tokens = cache_read
    return response


@patch("app.services.llm_gateway.anthropic.Anthropic")
def test_routing_dispatches_correct_model(mock_anthropic_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response()

    gw = LLMGateway()

    for tier, expected_model in TIER_MODEL_MAP.items():
        mock_client.messages.create.reset_mock()
        gw.complete("system", [Message("user", "hi")], tier=tier)  # type: ignore[arg-type]
        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == expected_model


@patch("app.services.llm_gateway.anthropic.Anthropic")
def test_system_prompt_gets_cache_control(mock_anthropic_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response()

    gw = LLMGateway()
    gw.complete("my system prompt", [Message("user", "hello")])

    call_kwargs = mock_client.messages.create.call_args.kwargs
    system_block = call_kwargs["system"]
    assert isinstance(system_block, list)
    assert system_block[0]["cache_control"] == {"type": "ephemeral"}
    assert system_block[0]["text"] == "my system prompt"


@patch("app.services.llm_gateway.anthropic.Anthropic")
def test_response_parses_usage(mock_anthropic_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response(
        text="answer",
        input_tokens=200,
        output_tokens=80,
        cache_creation=150,
        cache_read=0,
    )

    gw = LLMGateway()
    result = gw.complete("sys", [Message("user", "q")])

    assert result.text == "answer"
    assert result.usage.input_tokens == 200
    assert result.usage.output_tokens == 80
    assert result.usage.cache_creation_input_tokens == 150
    assert result.usage.cache_read_input_tokens == 0
    assert result.stop_reason == "end_turn"


@patch("app.services.llm_gateway.anthropic.Anthropic")
def test_cache_breakpoint_on_message(mock_anthropic_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response()

    gw = LLMGateway()
    gw.complete(
        "sys",
        [Message("user", "context"), Message("user", "question")],
        cache_breakpoints=[CacheBreakpoint(index=0)],
    )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    messages = call_kwargs["messages"]
    # message at index 0 should have cache_control
    assert isinstance(messages[0]["content"], list)
    assert messages[0]["content"][0]["cache_control"] == {"type": "ephemeral"}
    # message at index 1 should be plain string
    assert isinstance(messages[1]["content"], str)
