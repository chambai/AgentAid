from datetime import datetime, timedelta

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


@pytest.mark.asyncio
async def test_attribution_drift_tick_detects_shift(tmp_path, monkeypatch) -> None:
    """Reference is the early citation distribution; later runs that
    concentrate on different papers should produce a non-zero PSI and trip
    the threshold."""
    monkeypatch.setenv("AGENTAID_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'a.db'}")
    import importlib

    import agentaid_server.config as cfg
    import agentaid_server.db.engine as eng
    importlib.reload(cfg)
    importlib.reload(eng)
    import agentaid_server.orchestrator.drift_workers as dw
    from agentaid_server.db.engine import SessionLocal, init_db
    from agentaid_server.db.models import DriftStateRow
    from agentaid_server.db.models import Run as RunRow
    importlib.reload(dw)
    dw._attribution_reference = None
    await init_db()

    base = datetime(2026, 1, 1)
    early_attr = {"paper-A": 0.6, "paper-B": 0.4}
    late_attr = {"paper-X": 0.7, "paper-Y": 0.3}

    async with SessionLocal() as s:
        for i in range(15):
            s.add(RunRow(
                id=f"early-{i}", agent_name="arxiv-planner",
                started_at=base + timedelta(minutes=i),
                ended_at=base + timedelta(minutes=i, seconds=30),
                status="succeeded",
                input={"research_interest": "x"},
                output={"digest": "d", "candidates": [], "sections": [],
                        "figures": {}, "attribution": early_attr},
            ))
        for i in range(20):
            s.add(RunRow(
                id=f"late-{i}", agent_name="arxiv-planner",
                started_at=base + timedelta(hours=1, minutes=i),
                ended_at=base + timedelta(hours=1, minutes=i, seconds=30),
                status="succeeded",
                input={"research_interest": "x"},
                output={"digest": "d", "candidates": [], "sections": [],
                        "figures": {}, "attribution": late_attr},
            ))
        await s.commit()

    await dw.attribution_drift_tick()

    async with SessionLocal() as s:
        rows = (await s.exec(select(DriftStateRow)
                             .where(DriftStateRow.signal == "attribution"))).all()
    assert rows, "expected attribution drift state row"
    assert rows[-1].detector_name == "psi:citation_weight"
    assert rows[-1].value > 0.5, "fully disjoint citation sets should yield large PSI"
    assert rows[-1].is_drifted


@pytest.mark.asyncio
async def test_attribution_drift_tick_skips_without_data(tmp_path, monkeypatch) -> None:
    """Below the reference threshold, no row should be written and no
    reference should be frozen."""
    monkeypatch.setenv("AGENTAID_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'a2.db'}")
    import importlib

    import agentaid_server.config as cfg
    import agentaid_server.db.engine as eng
    importlib.reload(cfg)
    importlib.reload(eng)
    import agentaid_server.orchestrator.drift_workers as dw
    from agentaid_server.db.engine import SessionLocal, init_db
    from agentaid_server.db.models import DriftStateRow
    importlib.reload(dw)
    dw._attribution_reference = None
    await init_db()

    await dw.attribution_drift_tick()

    async with SessionLocal() as s:
        rows = (await s.exec(select(DriftStateRow)
                             .where(DriftStateRow.signal == "attribution"))).all()
    assert rows == []
    assert dw._attribution_reference is None
