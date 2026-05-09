import logging
import time
from dataclasses import dataclass
from typing import Iterator, Literal, Union

import anthropic
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.llm_models import TIER_MODEL_MAP, Tier

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: Literal["user", "assistant"]
    content: str


@dataclass
class CacheBreakpoint:
    index: int  # message index to attach cache_control to


@dataclass
class UsageInfo:
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int


@dataclass
class LLMResponse:
    text: str
    model: str
    usage: UsageInfo
    stop_reason: str


@dataclass
class StreamDelta:
    type: Literal["delta"]
    text: str


@dataclass
class StreamDone:
    type: Literal["done"]
    usage: UsageInfo
    stop_reason: str
    model: str


StreamEvent = Union[StreamDelta, StreamDone]


def _is_overloaded(exc: BaseException) -> bool:
    return isinstance(exc, anthropic.APIStatusError) and exc.status_code == 529


class LLMGateway:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def complete(
        self,
        system: str,
        messages: list[Message],
        tier: Tier = "default",
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        return self._call(system, messages, tier, cache_breakpoints, max_tokens)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=8),
        retry=retry_if_exception(_is_overloaded),
        reraise=True,
    )
    def _call(
        self,
        system: str,
        messages: list[Message],
        tier: Tier,
        cache_breakpoints: list[CacheBreakpoint] | None,
        max_tokens: int,
    ) -> LLMResponse:
        model = TIER_MODEL_MAP[tier]
        system_block = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

        api_messages: list[dict[str, object]] = []
        for i, msg in enumerate(messages):
            content: list[dict[str, object]] | str
            if cache_breakpoints and any(bp.index == i for bp in cache_breakpoints):
                content = [{"type": "text", "text": msg.content, "cache_control": {"type": "ephemeral"}}]
            else:
                content = msg.content
            api_messages.append({"role": msg.role, "content": content})

        start = time.monotonic()
        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_block,  # type: ignore[arg-type]
            messages=api_messages,  # type: ignore[arg-type]
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        usage = response.usage
        cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

        logger.info(
            "llm_call",
            extra={
                "model": model,
                "tier": tier,
                "tokens_in": usage.input_tokens,
                "tokens_out": usage.output_tokens,
                "cache_read": cache_read,
                "cache_create": cache_creation,
                "latency_ms": latency_ms,
            },
        )

        text = response.content[0].text if response.content else ""
        return LLMResponse(
            text=text,
            model=model,
            usage=UsageInfo(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_creation_input_tokens=cache_creation,
                cache_read_input_tokens=cache_read,
            ),
            stop_reason=response.stop_reason or "",
        )

    def complete_stream(
        self,
        system: str,
        messages: list[Message],
        tier: Tier = "default",
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        max_tokens: int = 1024,
    ) -> Iterator[StreamEvent]:
        """Streaming variant of complete(). Yields StreamDelta events with text deltas,
        followed by exactly one StreamDone event with final usage + stop_reason.

        Retries on overloaded errors before the stream begins. Once streaming starts,
        any error propagates to the caller (no mid-stream retry — partial output is unsafe to retry).
        """
        return self._call_stream(system, messages, tier, cache_breakpoints, max_tokens)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=8),
        retry=retry_if_exception(_is_overloaded),
        reraise=True,
    )
    def _open_stream(
        self,
        model: str,
        system_block: list[dict[str, object]],
        api_messages: list[dict[str, object]],
        max_tokens: int,
    ):
        return self._client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system_block,  # type: ignore[arg-type]
            messages=api_messages,  # type: ignore[arg-type]
        )

    def _call_stream(
        self,
        system: str,
        messages: list[Message],
        tier: Tier,
        cache_breakpoints: list[CacheBreakpoint] | None,
        max_tokens: int,
    ) -> Iterator[StreamEvent]:
        model = TIER_MODEL_MAP[tier]
        system_block = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

        api_messages: list[dict[str, object]] = []
        for i, msg in enumerate(messages):
            content: list[dict[str, object]] | str
            if cache_breakpoints and any(bp.index == i for bp in cache_breakpoints):
                content = [{"type": "text", "text": msg.content, "cache_control": {"type": "ephemeral"}}]
            else:
                content = msg.content
            api_messages.append({"role": msg.role, "content": content})

        start = time.monotonic()
        stream_ctx = self._open_stream(model, system_block, api_messages, max_tokens)

        with stream_ctx as stream:
            for delta in stream.text_stream:
                yield StreamDelta(type="delta", text=delta)

            final = stream.get_final_message()
            usage = final.usage
            cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
            cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
            latency_ms = int((time.monotonic() - start) * 1000)

            logger.info(
                "llm_call_stream",
                extra={
                    "model": model,
                    "tier": tier,
                    "tokens_in": usage.input_tokens,
                    "tokens_out": usage.output_tokens,
                    "cache_read": cache_read,
                    "cache_create": cache_creation,
                    "latency_ms": latency_ms,
                },
            )

            yield StreamDone(
                type="done",
                usage=UsageInfo(
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cache_creation_input_tokens=cache_creation,
                    cache_read_input_tokens=cache_read,
                ),
                stop_reason=final.stop_reason or "",
                model=model,
            )
