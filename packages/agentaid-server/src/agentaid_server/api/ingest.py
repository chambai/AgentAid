from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, status
from sqlmodel import select

from agentaid.otel.conventions import AgentAid

from ..db import engine as _db_engine
from ..db.models import Run, Span
from ..ingestion.parser import derive_run, parse_span
from ..orchestrator import run_invariants, run_online


def _decode_attr(value: object) -> object:
    """Span attributes are scalars/strings on the wire. agentaid.input and
    agentaid.output are JSON-encoded strings — decode them back to dicts so
    they can be stored as JSON columns directly.
    """
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value
    return value

router = APIRouter()

@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest(payload: dict, bg: BackgroundTasks) -> dict[str, int]:
    raw_spans = payload.get("spans", [])
    parsed = [parse_span(r) for r in raw_spans]

    # Resolve run_id per trace by finding the root span carrying agentaid.run_id;
    # propagate that run_id to child spans in the same trace if they lack it.
    # Falls back to using the trace_id itself when no agentaid.run_id is set.
    by_trace: dict[str, list[Span]] = {}
    raw_by_span: dict[str, dict] = {r["span_id"]: r for r in raw_spans}
    for s in parsed:
        raw = raw_by_span.get(s.id, {})
        trace_id = raw.get("trace_id", "")
        by_trace.setdefault(trace_id, []).append(s)

    trace_run_id: dict[str, str] = {}
    for trace_id, spans in by_trace.items():
        root_run = next(
            (s.run_id for s in spans if s.parent_span_id is None and s.run_id),
            "",
        )
        any_run = next((s.run_id for s in spans if s.run_id), "") if not root_run else root_run
        trace_run_id[trace_id] = any_run or f"trace-{trace_id[:16]}"

    by_run: dict[str, list[Span]] = {}
    for trace_id, spans in by_trace.items():
        run_id = trace_run_id[trace_id]
        for s in spans:
            if not s.run_id:
                s.run_id = run_id
            by_run.setdefault(s.run_id, []).append(s)

    inserted_spans = 0
    upserted_runs = 0
    async with _db_engine.SessionLocal() as session:
        for run_id, spans in by_run.items():
            existing = (await session.exec(select(Run).where(Run.id == run_id))).first()
            if existing is None:
                derived = derive_run(spans)
                if derived is not None:
                    session.add(derived)
                    upserted_runs += 1
            else:
                root = next((s for s in spans if s.parent_span_id is None), None)
                if root and root.ended_at:
                    existing.ended_at = root.ended_at
                    existing.status = "succeeded"
                    # Pull agentaid.input / agentaid.output off the root span
                    # if the placeholder row didn't have them yet. This is
                    # the path POST /digests takes — the placeholder is
                    # created with input only; the agent fills in output via
                    # this attribute when it finishes.
                    attrs = root.attributes or {}
                    raw_input = attrs.get(AgentAid.INPUT)
                    if raw_input is not None and not existing.input:
                        existing.input = _decode_attr(raw_input)  # type: ignore[assignment]
                    raw_output = attrs.get(AgentAid.OUTPUT)
                    if raw_output is not None:
                        decoded = _decode_attr(raw_output)
                        existing.output = decoded  # type: ignore[assignment]
                        # If the agent recorded an explicit error in its
                        # output, mark the run as failed so the consumer UI
                        # surfaces a clear error rather than "silent failure".
                        if isinstance(decoded, dict) and decoded.get("error"):
                            existing.status = "failed"
                    session.add(existing)
            for s in spans:
                in_db = await session.get(Span, s.id)
                if in_db is None:
                    session.add(s)
                    inserted_spans += 1
                else:
                    in_db.ended_at = s.ended_at
                    in_db.attributes = s.attributes
                    in_db.events = s.events
                    session.add(in_db)
        await session.commit()

    for run_id, spans in by_run.items():
        if any(sp.parent_span_id is None and sp.ended_at for sp in spans):
            bg.add_task(run_invariants, run_id)
            bg.add_task(run_online, run_id)

    return {"runs": upserted_runs, "spans": inserted_spans}
