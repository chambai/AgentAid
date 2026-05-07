from __future__ import annotations

import json as _json
from dataclasses import dataclass

from . import llm
from .mock_arxiv.client import get_arxiv_client
from .mock_arxiv.mock import Paper, PaperSummary


@dataclass(frozen=True)
class CandidateScore:
    paper_id: str
    score: float
    rationale: str


@dataclass(frozen=True)
class FigureDescription:
    paper_id: str
    caption: str
    description: str
    filename: str | None = None


@dataclass(frozen=True)
class Summary:
    paper_id: str
    text: str


# ---------------------------------------------------------------------------
# Run-scoped figure side-channel.
#
# The agent's planner/worker stack is supposed to thread figure data through
# WorkerResult.figure_descriptions and PlannerResult.figures, but the LLM is
# unreliable at it (figures are deterministic data, not a judgment call).
# Anything that calls extract_figures() below records the figures into this
# module-level dict, keyed by paper_id. __main__.py resets the dict at the
# start of each run and reads it at the end, then merges with whatever the
# LLM did populate. Because this is the lowest-level data tap (the plain
# async function that *every* layer above eventually delegates to), we can't
# miss figures regardless of how the agent loop chooses to surface them.
#
# Single-tenant dev: a module-level dict is fine. For concurrent runs in a
# multi-tenant deployment, the equivalent should be a per-run keyed store
# (e.g., keyed off agentaid.run_id from the OTel context).
# ---------------------------------------------------------------------------
_RUN_FIGURES: dict[str, list[dict]] = {}


def reset_run_figures() -> None:
    """Clear the run-scoped figure side-channel. Call before each agent run."""
    _RUN_FIGURES.clear()


def get_run_figures() -> dict[str, list[dict]]:
    """Read the figures captured during this run, keyed by paper_id."""
    return dict(_RUN_FIGURES)


# Internal indirection so tests can monkeypatch.
async def _llm_json(prompt: str) -> str:
    raw = await llm.text(prompt + "\n\nRespond with a single valid JSON object, no prose.")
    start, end = raw.find("{"), raw.rfind("}")
    return raw[start:end + 1] if start != -1 and end != -1 else raw


async def search_arxiv(
    query: str, limit: int = 10,
    date_from: str | None = None, date_to: str | None = None,
) -> list[PaperSummary]:
    return get_arxiv_client().search(query, limit=limit, date_from=date_from, date_to=date_to)


async def fetch_metadata(paper_id: str) -> PaperSummary:
    return get_arxiv_client().fetch_metadata(paper_id)


async def fetch_paper(paper_id: str) -> Paper:
    return get_arxiv_client().fetch_paper(paper_id)


async def score_candidate(metadata_id: str, research_interest: str) -> CandidateScore:
    meta = get_arxiv_client().fetch_metadata(metadata_id)
    prompt = (
        f"Research interest: {research_interest}\n\n"
        f"Paper title: {meta.title}\n"
        f"Abstract: {meta.abstract}\n\n"
        "How relevant is this paper to the research interest? "
        "Return JSON with fields: score (float 0..1), rationale (one short sentence)."
    )
    data = _json.loads(await _llm_json(prompt))
    return CandidateScore(paper_id=metadata_id,
                          score=float(data["score"]),
                          rationale=str(data["rationale"]))


async def extract_figures(paper_id: str) -> list[FigureDescription]:
    figs = get_arxiv_client().extract_figures(paper_id)
    out: list[FigureDescription] = []
    for f in figs:
        desc = await llm.vision(
            "Describe what this figure shows in 1-2 sentences. Be specific.",
            f.data, content_type=f.content_type,
        )
        out.append(FigureDescription(paper_id=paper_id, caption=f.caption, description=desc, filename=f.filename))
    # Record into the run-scoped side-channel. Whatever the agent loop
    # decides to do with the returned list, the figures still land in
    # _RUN_FIGURES and __main__.py picks them up at the end of the run.
    _RUN_FIGURES[paper_id] = [
        {"caption": d.caption, "description": d.description, "filename": d.filename}
        for d in out
    ]
    return out


async def summarize(paper_id: str, focus: str) -> Summary:
    paper = get_arxiv_client().fetch_paper(paper_id)
    prompt = (
        f"Summarize the following paper with focus on '{focus}'. "
        "3-5 bullets, terse, technical voice.\n\n"
        f"Title: {paper.title}\n\n{paper.body[:6000]}"
    )
    summary = await llm.text(prompt, max_tokens=600)
    return Summary(paper_id=paper_id, text=summary)


async def query_paper(paper_id: str, question: str) -> str:
    paper = get_arxiv_client().fetch_paper(paper_id)
    prompt = (
        f"Paper: {paper.title}\n\n{paper.body[:8000]}\n\n"
        f"Question: {question}\n\nAnswer concisely, citing specific text where useful."
    )
    return await llm.text(prompt, max_tokens=600, model=llm.QUALITY)


async def compose_digest(papers: list[Summary], research_interest: str) -> str:
    bullets = "\n\n".join(f"### {s.paper_id}\n{s.text}" for s in papers)
    prompt = (
        f"You are producing a weekly research digest for: {research_interest}\n\n"
        "Compose a Markdown digest with:\n"
        "1. A 2-sentence overview tying the papers together.\n"
        "2. Per-paper sections (already drafted below) - keep them.\n"
        "3. A 'What this means for practitioners' closing of 2-3 bullets.\n\n"
        f"Drafted summaries:\n\n{bullets}"
    )
    return await llm.text(prompt, max_tokens=2000, model=llm.QUALITY)
