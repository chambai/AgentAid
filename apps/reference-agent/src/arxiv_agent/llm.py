from __future__ import annotations

import base64
import json
import os

from anthropic import AsyncAnthropic
from opentelemetry import trace as _trace

from agentaid.otel.conventions import GenAI

_client: AsyncAnthropic | None = None
_tracer = _trace.get_tracer("arxiv_agent.llm")

# Chars stored in gen_ai.prompt / gen_ai.completion span attributes.
# Long enough to be useful; short enough to avoid bloating the DB.
_PROMPT_LIMIT = 4000
_COMPLETION_LIMIT = 2000


def _get() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic()
    return _client


CHEAP = os.getenv("AGENTAID_CHEAP_MODEL", "claude-haiku-4-5")
QUALITY = os.getenv("AGENTAID_QUALITY_MODEL", "claude-sonnet-4-6")


async def text(prompt: str, *, model: str = CHEAP, system: str | None = None,
               max_tokens: int = 1024) -> str:
    with _tracer.start_as_current_span("llm.text") as span:
        span.set_attribute(GenAI.SYSTEM, "anthropic")
        span.set_attribute(GenAI.REQUEST_MODEL, model)
        span.set_attribute(GenAI.OPERATION_NAME, "chat")
        span.set_attribute("gen_ai.prompt", prompt[:_PROMPT_LIMIT])
        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        msg = await _get().messages.create(**kwargs)
        result = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
        span.set_attribute(GenAI.USAGE_INPUT_TOKENS, msg.usage.input_tokens)
        span.set_attribute(GenAI.USAGE_OUTPUT_TOKENS, msg.usage.output_tokens)
        span.set_attribute("gen_ai.completion", result[:_COMPLETION_LIMIT])
        return result


async def vision(prompt: str, image_bytes: bytes, content_type: str = "image/jpeg",
                 *, model: str = CHEAP, max_tokens: int = 512) -> str:
    with _tracer.start_as_current_span("llm.vision") as span:
        span.set_attribute(GenAI.SYSTEM, "anthropic")
        span.set_attribute(GenAI.REQUEST_MODEL, model)
        span.set_attribute(GenAI.OPERATION_NAME, "chat")
        span.set_attribute("gen_ai.prompt", prompt[:_PROMPT_LIMIT])
        span.set_attribute("gen_ai.content_type", content_type)
        image_b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        content = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": content_type, "data": image_b64},
            },
            {"type": "text", "text": prompt},
        ]
        msg = await _get().messages.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": content}],
        )
        result = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
        span.set_attribute(GenAI.USAGE_INPUT_TOKENS, msg.usage.input_tokens)
        span.set_attribute(GenAI.USAGE_OUTPUT_TOKENS, msg.usage.output_tokens)
        span.set_attribute("gen_ai.completion", result[:_COMPLETION_LIMIT])
        return result


async def json_call(prompt: str, *, model: str = CHEAP, max_tokens: int = 512) -> dict:
    # text() is already instrumented — json_call's span is its child.
    raw = await text(prompt + "\n\nRespond with a single valid JSON object, no prose.",
                     model=model, max_tokens=max_tokens)
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON in response: {raw!r}")
    return json.loads(raw[start:end + 1])
