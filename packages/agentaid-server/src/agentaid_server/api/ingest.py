from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, status
from sqlmodel import select

from ..db import engine as _db_engine
from ..db.models import Run, Span
from ..ingestion.parser import derive_run, parse_span
from ..orchestrator import run_invariants, run_online

router = APIRouter()

@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest(payload: dict, bg: BackgroundTasks) -> dict[str, int]:
    raw_spans = payload.get("spans", [])
    parsed = [parse_span(r) for r in raw_spans]

    by_run: dict[str, list[Span]] = {}
    for s in parsed:
        if not s.run_id:
            continue
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
