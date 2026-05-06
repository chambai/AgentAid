from __future__ import annotations
import base64
import json
import os
from anthropic import AsyncAnthropic

_client: AsyncAnthropic | None = None


def _get() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic()
    return _client


CHEAP = os.getenv("AGENTAID_CHEAP_MODEL", "claude-haiku-4-5")
QUALITY = os.getenv("AGENTAID_QUALITY_MODEL", "claude-sonnet-4-6")


async def text(prompt: str, *, model: str = CHEAP, system: str | None = None,
               max_tokens: int = 1024) -> str:
    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    msg = await _get().messages.create(**kwargs)
    return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")


async def vision(prompt: str, image_bytes: bytes, content_type: str = "image/jpeg",
                 *, model: str = CHEAP, max_tokens: int = 512) -> str:
    image_b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": content_type, "data": image_b64}},
        {"type": "text", "text": prompt},
    ]
    msg = await _get().messages.create(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "user", "content": content}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")


async def json_call(prompt: str, *, model: str = CHEAP, max_tokens: int = 512) -> dict:
    raw = await text(prompt + "\n\nRespond with a single valid JSON object, no prose.",
                     model=model, max_tokens=max_tokens)
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON in response: {raw!r}")
    return json.loads(raw[start:end + 1])
