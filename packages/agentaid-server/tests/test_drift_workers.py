from datetime import datetime

import pytest
from sqlmodel import select


@pytest.mark.asyncio
async def test_quality_drift_tick_writes_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTAID_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'d.db'}")
    import importlib

    import agentaid_server.config as cfg
    import agentaid_server.db.engine as eng
    importlib.reload(cfg)
    importlib.reload(eng)
    # Reload drift_workers AFTER engine reload so it picks up new SessionLocal binding.
    import agentaid_server.orchestrator.drift_workers as dw
    from agentaid_server.db.engine import SessionLocal, init_db
    from agentaid_server.db.models import DriftStateRow, EvalResult
    importlib.reload(dw)
    # Reset module-level detector singletons
    dw._quality_detectors.clear()
    dw._tool_detectors.clear()
    dw._input_detector = None
    await init_db()
    async with SessionLocal() as s:
        for i in range(60):
            score = 0.85 if i < 30 else 0.4
            s.add(EvalResult(run_id=f"r{i}", eval_name="relevance_judge",
                             mode="online", score=score,
                             created_at=datetime.utcnow()))
        await s.commit()

    await dw.quality_drift_tick()

    async with SessionLocal() as s:
        rows = (await s.exec(select(DriftStateRow).where(DriftStateRow.signal == "quality"))).all()
    assert rows, "expected at least one quality drift state row"
    assert any(r.is_drifted for r in rows)
