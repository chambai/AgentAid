from __future__ import annotations
import asyncio
import logging
import numpy as np
from sqlmodel import select
from agentaid.drift import ADWIN, MMDDetector, PSIDetector
from ..db import engine as _db_engine
from ..db.models import EvalResult, Span, DriftStateRow, Run as RunRow

log = logging.getLogger(__name__)

_quality_detectors: dict[str, ADWIN] = {}
_tool_detectors: dict[str, PSIDetector] = {}
_input_detector: MMDDetector | None = None

_TOOL_REFERENCE: dict[str, dict[str, float]] = {
    "planner": {"search_arxiv": 1.0, "fetch_metadata": 4.0,
                "score_candidate": 4.0, "compose_digest": 1.0,
                "dispatch_worker": 3.0},
    "worker":  {"fetch_paper": 3.0, "extract_figures": 3.0,
                "summarize": 3.0, "query_paper": 0.5},
}

async def quality_drift_tick() -> None:
    """ADWIN over recent eval scores per eval_name."""
    async with _db_engine.SessionLocal() as s:
        rows = (await s.exec(select(EvalResult).where(EvalResult.eval_name == "relevance_judge")
                              .order_by(EvalResult.created_at))).all()
    if not rows:
        return
    det = _quality_detectors.setdefault("relevance_judge", ADWIN(delta=1.0))
    last_drifted = False
    for r in rows:
        last_drifted = det.update(float(r.score)) or last_drifted

    async with _db_engine.SessionLocal() as s:
        s.add(DriftStateRow(
            signal="quality", detector_name="adwin",
            window=str(len(rows)), value=det.value(),
            threshold=det.threshold(),
            is_drifted=det.is_drifted() or last_drifted,
        ))
        await s.commit()

async def tool_call_drift_tick() -> None:
    """PSI per agent role over recent tool-call spans."""
    async with _db_engine.SessionLocal() as s:
        spans = (await s.exec(select(Span).where(Span.role.in_(["planner", "worker"]))
                              .order_by(Span.started_at.desc()).limit(500))).all()
    by_role: dict[str, list[str]] = {"planner": [], "worker": []}
    for sp in spans:
        role = sp.role
        if role in by_role and sp.parent_span_id is not None:
            by_role[role].append(sp.name)
    state_rows: list[DriftStateRow] = []
    for role, calls in by_role.items():
        if not calls:
            continue
        det = _tool_detectors.setdefault(role,
            PSIDetector(reference=_TOOL_REFERENCE[role], threshold=0.2, window=200))
        for name in calls:
            det.update(name)
        state_rows.append(DriftStateRow(
            signal="tool_call", detector_name=f"psi:{role}",
            window=str(len(calls)), value=det.value(),
            threshold=det.threshold(), is_drifted=det.is_drifted(),
        ))
    if state_rows:
        async with _db_engine.SessionLocal() as s:
            for r in state_rows:
                s.add(r)
            await s.commit()

async def input_drift_tick() -> None:
    """MMD on hashed user-input embeddings (placeholder; real embeddings later)."""
    global _input_detector
    async with _db_engine.SessionLocal() as s:
        rows = (await s.exec(select(RunRow).order_by(RunRow.started_at).limit(1000))).all()
    if not rows:
        return

    def embed(text: str) -> np.ndarray:
        rng = np.random.default_rng(abs(hash(text)) % (2**32))
        return rng.normal(0, 1, size=8)

    interests = [(r.input or {}).get("research_interest", "") for r in rows]
    if len(interests) < 50:
        return
    if _input_detector is None:
        refs = np.stack([embed(x) for x in interests[:50]], axis=0)
        _input_detector = MMDDetector(reference=refs, threshold=0.05, window=50)
    last_drifted = False
    for x in interests[50:]:
        last_drifted = _input_detector.update(embed(x)) or last_drifted

    async with _db_engine.SessionLocal() as s2:
        s2.add(DriftStateRow(
            signal="input", detector_name="mmd_rbf",
            window=str(len(interests)),
            value=_input_detector.value(),
            threshold=_input_detector.threshold(),
            is_drifted=_input_detector.is_drifted() or last_drifted,
        ))
        await s2.commit()

async def drift_loop(interval_s: float = 5.0) -> None:
    while True:
        try:
            await asyncio.gather(quality_drift_tick(), tool_call_drift_tick(), input_drift_tick())
        except Exception:
            log.exception("drift tick failed")
        await asyncio.sleep(interval_s)
