"""Seed AgentAid with synthetic data designed to fire each drift detector.

Usage:
    uv run python scripts/seed_drift.py [--db sqlite+aiosqlite:///./agentaid.db]

Produces 100 synthetic runs across two epochs (0..49 stable, 50..99 shifted),
600+ spans, 100 eval results — designed to drive ADWIN (quality), PSI
(tool-call), and MMD (input embedding hash) into the drifted state on the
next worker tick.
"""
from __future__ import annotations
import argparse
import asyncio
import os
import random
from datetime import datetime, timedelta

EPOCHS = [
    {"interest": "concept drift in streaming ML",
     "tools": ["fetch_paper", "extract_figures", "summarize"]},
    {"interest": "transformer alignment in robotics",
     "tools": ["fetch_paper", "extract_figures", "extract_figures",
               "extract_figures", "summarize"]},
]

async def seed(db_url: str | None) -> None:
    if db_url:
        os.environ["AGENTAID_DB_URL"] = db_url
    # Import after env is set so engine binds correctly.
    import importlib
    import agentaid_server.config as cfg
    import agentaid_server.db.engine as eng
    importlib.reload(cfg); importlib.reload(eng)
    from agentaid_server.db.engine import init_db, SessionLocal
    from agentaid_server.db.models import Run, Span, EvalResult

    await init_db()
    base = datetime.utcnow() - timedelta(days=2)

    async with SessionLocal() as s:
        for i in range(100):
            epoch = EPOCHS[0] if i < 50 else EPOCHS[1]
            run_id = f"seed-{i:04d}"
            run_started = base + timedelta(minutes=i * 5)
            run_ended = run_started + timedelta(seconds=12)
            s.add(Run(id=run_id, agent_name="arxiv-planner",
                      started_at=run_started, ended_at=run_ended,
                      status="succeeded",
                      total_cost=0.02 + random.uniform(0, 0.005),
                      total_tokens=2000 + random.randint(0, 500),
                      input={"research_interest": epoch["interest"]},
                      output={"digest": "## P\n- summary\n2401.00001"}))
            s.add(Span(id=f"{run_id}-p", run_id=run_id, parent_span_id=None,
                       name="planner", role="planner",
                       started_at=run_started, ended_at=run_ended,
                       attributes={}, events=[]))
            for j, tool in enumerate(epoch["tools"]):
                start = run_started + timedelta(seconds=1 + j)
                s.add(Span(id=f"{run_id}-t{j}", run_id=run_id,
                           parent_span_id=f"{run_id}-p",
                           name=tool, role="worker",
                           started_at=start,
                           ended_at=start + timedelta(seconds=1),
                           attributes={"agentaid.role": "worker"}, events=[]))
            score = random.gauss(0.85, 0.04) if i < 50 else random.gauss(0.40, 0.05)
            s.add(EvalResult(run_id=run_id, eval_name="relevance_judge",
                             mode="online",
                             score=max(0.0, min(1.0, score)),
                             label="judged", rationale="seeded",
                             created_at=run_ended))
        await s.commit()
    print(f"Seeded 100 runs to {os.getenv('AGENTAID_DB_URL', 'default')}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=None)
    args = p.parse_args()
    asyncio.run(seed(args.db))
