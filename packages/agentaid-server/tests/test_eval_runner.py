import pytest
from datetime import datetime
from sqlmodel import select

@pytest.mark.asyncio
async def test_run_invariants_writes_results(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTAID_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'e.db'}")
    import importlib, agentaid_server.config as cfg, agentaid_server.db.engine as eng
    importlib.reload(cfg); importlib.reload(eng)
    from agentaid_server.db.engine import SessionLocal, init_db
    from agentaid_server.db.models import Run, EvalResult
    from agentaid_server.orchestrator.eval_runner import run_invariants
    await init_db()
    async with SessionLocal() as s:
        s.add(Run(id="rx", agent_name="a", started_at=datetime.utcnow(),
                  ended_at=datetime.utcnow(), status="succeeded", total_cost=0.01,
                  output={"digest": "## p\n- s\n2401.00001"}))
        await s.commit()

    await run_invariants("rx")

    async with SessionLocal() as s:
        rows = (await s.exec(select(EvalResult).where(EvalResult.run_id == "rx"))).all()
    names = {r.eval_name for r in rows}
    assert "structural_completeness" in names
    assert "cost_within_budget" in names
