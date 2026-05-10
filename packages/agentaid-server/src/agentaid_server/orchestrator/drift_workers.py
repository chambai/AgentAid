from __future__ import annotations

import asyncio
import logging
import math

import numpy as np
from agentaid.drift import ADWIN, MMDDetector, PSIDetector
from sqlmodel import select

from ..db import engine as _db_engine
from ..db.models import DriftStateRow, EvalResult, Span
from ..db.models import Run as RunRow

log = logging.getLogger(__name__)

_quality_detectors: dict[str, ADWIN] = {}
_tool_detectors: dict[str, PSIDetector] = {}
_input_detector: MMDDetector | None = None
_attribution_reference: dict[str, float] | None = None

# Tunables for attribution drift. Reference threshold is intentionally low
# so the worker stops returning "no data yet" after a small number of live
# runs in dev. Production tuning would raise this and add a manual reset
# endpoint when the agent is intentionally retrained.
_ATTRIBUTION_REFERENCE_THRESHOLD = 10
_ATTRIBUTION_RECENT_WINDOW = 50
_ATTRIBUTION_PSI_THRESHOLD = 0.2
_ATTRIBUTION_SMOOTHING = 1e-4

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

def _aggregate_attribution(runs: list[RunRow]) -> dict[str, float]:
    """Sum per-paper attribution weights across runs, then renormalise to 1."""
    agg: dict[str, float] = {}
    for r in runs:
        attr = (r.output or {}).get("attribution") if r.output else None
        if not isinstance(attr, dict):
            continue
        for paper_id, weight in attr.items():
            try:
                w = float(weight)
            except (TypeError, ValueError):
                continue
            agg[str(paper_id)] = agg.get(str(paper_id), 0.0) + w
    total = sum(agg.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in agg.items()}


def _psi(current: dict[str, float], reference: dict[str, float],
         smoothing: float) -> float:
    """PSI(current || reference) over the union of paper_ids.

    Same equation the streaming PSIDetector uses, but operating directly
    on aggregated distributions rather than a sample buffer. Citation
    attribution is naturally per-run (a distribution per digest), not a
    stream of single categorical samples.
    """
    keys = set(current) | set(reference)
    psi = 0.0
    for k in keys:
        cur = max(current.get(k, 0.0), smoothing)
        ref = max(reference.get(k, 0.0), smoothing)
        psi += (cur - ref) * math.log(cur / ref)
    return float(psi)


async def attribution_drift_tick() -> None:
    """PSI on the per-paper citation attribution distribution.

    Reference is the aggregate over the first N succeeded runs that emit a
    non-empty attribution dict; once frozen, every subsequent tick compares
    the aggregate over the most-recent runs against it. Detects the agent
    shifting which sources it relies on, even when output quality and
    tool-call patterns look unchanged.
    """
    global _attribution_reference
    async with _db_engine.SessionLocal() as s:
        runs = (await s.exec(select(RunRow)
                              .where(RunRow.status == "succeeded")
                              .order_by(RunRow.started_at).limit(500))).all()

    eligible = [r for r in runs
                if r.output and isinstance(r.output.get("attribution"), dict)
                and r.output["attribution"]]
    if not eligible:
        return

    if _attribution_reference is None:
        if len(eligible) < _ATTRIBUTION_REFERENCE_THRESHOLD:
            return
        _attribution_reference = _aggregate_attribution(
            eligible[:_ATTRIBUTION_REFERENCE_THRESHOLD])
        if not _attribution_reference:
            return

    current = _aggregate_attribution(eligible[-_ATTRIBUTION_RECENT_WINDOW:])
    if not current:
        return

    psi = _psi(current, _attribution_reference, _ATTRIBUTION_SMOOTHING)
    drifted = psi >= _ATTRIBUTION_PSI_THRESHOLD

    async with _db_engine.SessionLocal() as s:
        s.add(DriftStateRow(
            signal="attribution",
            detector_name="psi:citation_weight",
            window=str(len(eligible)),
            value=psi,
            threshold=_ATTRIBUTION_PSI_THRESHOLD,
            is_drifted=drifted,
        ))
        await s.commit()


async def drift_loop(interval_s: float = 5.0) -> None:
    while True:
        try:
            await asyncio.gather(
                quality_drift_tick(),
                tool_call_drift_tick(),
                input_drift_tick(),
                attribution_drift_tick(),
            )
        except Exception:
            log.exception("drift tick failed")
        await asyncio.sleep(interval_s)
