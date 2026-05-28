from __future__ import annotations

import json
from datetime import UTC, datetime

from agentaid.otel.conventions import AgentAid, GenAI

from ..db.models import Run
from ..db.models import Span as DbSpan

# Anthropic pricing per million tokens (input, output).
# Keys are substrings matched against the model name returned by the API.
_PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5":  (0.80,  4.00),
    "claude-haiku-4":    (0.80,  4.00),
    "claude-3-5-haiku":  (0.80,  4.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-sonnet-4":   (3.00, 15.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-opus-4-7":   (15.00, 75.00),
    "claude-opus-4":     (15.00, 75.00),
    "claude-3-opus":     (15.00, 75.00),
}


def _cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    m = model.lower()
    for key, (in_rate, out_rate) in _PRICING.items():
        if key in m:
            return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000
    return 0.0


def compute_run_cost(spans: list[DbSpan]) -> tuple[float, int]:
    """Return (total_cost_usd, total_tokens) across all LLM spans in the batch."""
    total_cost = 0.0
    total_tokens = 0
    for span in spans:
        attrs = span.attributes or {}
        model = str(attrs.get(GenAI.REQUEST_MODEL) or attrs.get(GenAI.RESPONSE_MODEL) or "")
        inp = int(attrs.get(GenAI.USAGE_INPUT_TOKENS) or 0)
        out = int(attrs.get(GenAI.USAGE_OUTPUT_TOKENS) or 0)
        if model and (inp or out):
            total_cost += _cost_usd(model, inp, out)
            total_tokens += inp + out
    return total_cost, total_tokens


def _ts_from_nano(nano: int | None) -> datetime | None:
    if nano is None:
        return None
    return datetime.fromtimestamp(nano / 1e9, tz=UTC).replace(tzinfo=None)

def parse_span(raw: dict) -> DbSpan:
    attrs = dict(raw.get("attributes", {}))
    return DbSpan(
        id=raw["span_id"],
        run_id=str(attrs.get(AgentAid.RUN_ID, "")),
        parent_span_id=raw.get("parent_span_id"),
        name=raw["name"],
        role=attrs.get(AgentAid.ROLE),
        started_at=_ts_from_nano(raw["start_time_unix_nano"]) or datetime.utcnow(),
        ended_at=_ts_from_nano(raw.get("end_time_unix_nano")),
        attributes=attrs,
        events=list(raw.get("events", [])),
    )

def derive_run(spans: list[DbSpan]) -> Run | None:
    """Reconstruct a Run from the root-most span carrying agentaid.run_id."""
    candidates = [s for s in spans if s.run_id]
    if not candidates:
        return None
    root = next((s for s in candidates if s.parent_span_id is None), candidates[0])
    attrs = root.attributes or {}
    raw_input = attrs.get(AgentAid.INPUT)
    raw_output = attrs.get(AgentAid.OUTPUT)
    total_cost, total_tokens = compute_run_cost(spans)
    return Run(
        id=root.run_id,
        agent_name=str(attrs.get(AgentAid.AGENT_NAME, "unknown")),
        started_at=root.started_at,
        ended_at=root.ended_at,
        status="succeeded" if root.ended_at else "running",
        prompt_sha=attrs.get(AgentAid.PROMPT_SHA),
        model=attrs.get(GenAI.RESPONSE_MODEL) or attrs.get(GenAI.REQUEST_MODEL),
        total_cost=total_cost,
        total_tokens=total_tokens,
        input=json.loads(raw_input) if isinstance(raw_input, str) else raw_input,
        output=json.loads(raw_output) if isinstance(raw_output, str) else raw_output,
    )
