from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from ..db import engine as _db_engine
from ..db.models import Run

router = APIRouter()

_REPO_ROOT = Path(__file__).parents[5]


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

    if run is None:
        raise HTTPException(404, f"digest for run {run_id} not found")

    # For runs with no digest yet, return partial status so polling clients
    # can track progress (or surface a silent failure) without 404s. Includes
    # status=succeeded runs that produced no output (the agent crashed before
    # writing the OUTPUT span attribute) — the consumer UI uses this to
    # detect silent failures and stop spinning.
    if not (run.output and run.output.get("digest")):
        inp: dict[str, Any] = run.input or {}
        out: dict[str, Any] = run.output or {}
        return {
            "run_id": run.id,
            "research_interest": inp.get("research_interest"),
            "date_from": inp.get("date_from"),
            "date_to": inp.get("date_to"),
            "generated_at": run.ended_at.isoformat() if run.ended_at else None,
            "digest": "",
            "candidates": out.get("candidates") or [],
            "sections": out.get("sections") or [],
            "figures": out.get("figures") or {},
            "status": run.status,
            "error": out.get("error"),
        }

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
        "figures": output.get("figures") or {},
        "status": run.status,
        "error": output.get("error"),
    }


class CreateDigestRequest(BaseModel):
    research_interest: str
    date_from: str
    date_to: str
    model: str = "claude-sonnet-4-6"


async def _watch_subprocess(proc: asyncio.subprocess.Process, run_id: str) -> None:
    """Wait for the agent subprocess and mark the run failed if it exits non-zero."""
    returncode = await proc.wait()
    if returncode != 0:
        async with _db_engine.SessionLocal() as s:
            run = (await s.exec(select(Run).where(Run.id == run_id))).first()
            if run is not None and run.status == "running":
                run.status = "failed"
                run.ended_at = datetime.utcnow()
                s.add(run)
                await s.commit()


@router.post("/digests", status_code=202)
async def create_digest(req: CreateDigestRequest) -> dict:
    if not req.research_interest.strip():
        raise HTTPException(status_code=422, detail="research_interest must not be empty")

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "ANTHROPIC_API_KEY is not set in the server environment. "
                "Start the server with the key exported, e.g.: "
                "set -a; source .env; set +a; make server"
            ),
        )

    run_id = f"live-{uuid.uuid4().hex[:10]}"
    now = datetime.utcnow()

    async with _db_engine.SessionLocal() as s:
        run = Run(
            id=run_id,
            agent_name="arxiv-planner",
            started_at=now,
            status="running",
            input={
                "research_interest": req.research_interest,
                "date_from": req.date_from,
                "date_to": req.date_to,
            },
            output=None,
        )
        s.add(run)
        await s.commit()

    env = {**os.environ, "AGENTAID_RUN_ID": run_id, "PYTHONUNBUFFERED": "1"}
    agentaid_endpoint = os.environ.get("AGENTAID_ENDPOINT", "http://localhost:8001/ingest")
    env["AGENTAID_ENDPOINT"] = agentaid_endpoint

    proc = await asyncio.create_subprocess_exec(
        "uv", "run", "python", "-m", "arxiv_agent",
        req.research_interest, req.date_from, req.date_to,
        cwd=str(_REPO_ROOT),
        env=env,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    asyncio.create_task(_watch_subprocess(proc, run_id))

    return {"run_id": run_id, "status": "running"}
