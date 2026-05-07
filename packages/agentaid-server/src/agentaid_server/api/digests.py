from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from ..db import engine as _db_engine
from ..db.models import Run

router = APIRouter()


def _top_paper_title(output: dict[str, Any] | None) -> str | None:
    if output is None:
        return None
    candidates = output.get("candidates") or []
    if candidates:
        return candidates[0].get("title")
    sections = output.get("sections") or []
    if sections:
        return sections[0].get("paper_id")
    return None


@router.get("/digests")
async def list_digests(limit: int = 20) -> dict:
    async with _db_engine.SessionLocal() as s:
        stmt = select(Run).order_by(Run.started_at.desc()).limit(limit)
        rows = (await s.exec(stmt)).all()

    results = []
    for r in rows:
        if not (r.output and r.output.get("digest")):
            continue
        inp: dict[str, Any] = r.input or {}
        results.append({
            "run_id": r.id,
            "research_interest": inp.get("research_interest"),
            "date_from": inp.get("date_from"),
            "date_to": inp.get("date_to"),
            "generated_at": r.ended_at.isoformat() if r.ended_at else None,
            "top_paper_title": _top_paper_title(r.output),
        })

    return {"digests": results}


@router.get("/digests/{run_id}")
async def get_digest(run_id: str) -> dict:
    async with _db_engine.SessionLocal() as s:
        run = (await s.exec(select(Run).where(Run.id == run_id))).first()

    if run is None or not (run.output and run.output.get("digest")):
        raise HTTPException(404, f"digest for run {run_id} not found")

    inp: dict[str, Any] = run.input or {}
    output: dict[str, Any] = run.output or {}

    return {
        "run_id": run.id,
        "research_interest": inp.get("research_interest"),
        "date_from": inp.get("date_from"),
        "date_to": inp.get("date_to"),
        "generated_at": run.ended_at.isoformat() if run.ended_at else None,
        "digest": output.get("digest", ""),
        "candidates": output.get("candidates") or [],
        "sections": output.get("sections") or [],
    }
