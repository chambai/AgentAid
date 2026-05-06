from __future__ import annotations

import json
from datetime import UTC, datetime

from agentaid.otel.conventions import AgentAid, GenAI

from ..db.models import Run
from ..db.models import Span as DbSpan


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
    return Run(
        id=root.run_id,
        agent_name=str(attrs.get(AgentAid.AGENT_NAME, "unknown")),
        started_at=root.started_at,
        ended_at=root.ended_at,
        status="succeeded" if root.ended_at else "running",
        prompt_sha=attrs.get(AgentAid.PROMPT_SHA),
        model=attrs.get(GenAI.RESPONSE_MODEL) or attrs.get(GenAI.REQUEST_MODEL),
        total_cost=float(attrs.get("agentaid.total_cost", 0.0) or 0.0),
        total_tokens=int(attrs.get(GenAI.USAGE_INPUT_TOKENS, 0) or 0)
                    + int(attrs.get(GenAI.USAGE_OUTPUT_TOKENS, 0) or 0),
        input=json.loads(raw_input) if isinstance(raw_input, str) else raw_input,
        output=json.loads(raw_output) if isinstance(raw_output, str) else raw_output,
    )
