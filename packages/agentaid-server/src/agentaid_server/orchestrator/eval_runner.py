from __future__ import annotations

import asyncio
import logging
import random

from agentaid.eval import (
    registry,
    templates,  # noqa: F401  -- import triggers registration
)
from agentaid.models import EvalMode
from agentaid.models import Run as RunModel
from sqlmodel import select

from ..config import settings
from ..db import engine as _db_engine
from ..db.models import EvalResult, Run

log = logging.getLogger(__name__)

def _to_domain(run: Run) -> RunModel:
    return RunModel(
        id=run.id, agent_name=run.agent_name, started_at=run.started_at,
        ended_at=run.ended_at, input=run.input, output=run.output,
        prompt_sha=run.prompt_sha, model=run.model,
        total_cost=run.total_cost, total_tokens=run.total_tokens,
        status=run.status,  # type: ignore[arg-type]
    )

async def _persist(result) -> None:
    async with _db_engine.SessionLocal() as s:
        s.add(EvalResult(
            run_id=result.run_id, eval_name=result.eval_name,
            mode=result.mode.value if hasattr(result.mode, "value") else str(result.mode),
            score=result.score, label=result.label, rationale=result.rationale,
        ))
        await s.commit()

async def run_invariants(run_id: str) -> None:
    async with _db_engine.SessionLocal() as s:
        run = (await s.exec(select(Run).where(Run.id == run_id))).first()
    if run is None:
        log.warning("run %s not found for invariants", run_id)
        return
    domain = _to_domain(run)
    for spec in registry.evals_for_mode(EvalMode.INVARIANT):
        try:
            res = await spec.fn(domain, None)
            await _persist(res)
        except Exception:
            log.exception("invariant eval %s failed for run %s", spec.name, run_id)

async def run_online(run_id: str) -> None:
    if random.random() > settings.online_eval_sample_rate:
        return
    async with _db_engine.SessionLocal() as s:
        run = (await s.exec(select(Run).where(Run.id == run_id))).first()
    if run is None:
        return
    domain = _to_domain(run)
    tasks = []
    for spec in registry.evals_for_mode(EvalMode.ONLINE):
        tasks.append(asyncio.create_task(_run_one(spec, domain)))
    await asyncio.gather(*tasks, return_exceptions=True)

async def _run_one(spec, domain: RunModel) -> None:
    try:
        res = await spec.fn(domain, None)
        await _persist(res)
    except Exception:
        log.exception("online eval %s failed for run %s", spec.name, domain.id)
