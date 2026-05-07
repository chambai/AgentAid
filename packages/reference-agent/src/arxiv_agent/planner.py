from __future__ import annotations

from importlib.resources import files

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel

from . import tools
from .worker import WorkerInput, build_worker_agent


class PlannerInput(BaseModel):
    research_interest: str = Field(min_length=1)
    date_from: str
    date_to: str


class CandidateRecord(BaseModel):
    paper_id: str
    title: str
    score: float
    rationale: str


class PaperSection(BaseModel):
    paper_id: str
    summary: str


class PlannerResult(BaseModel):
    digest: str
    candidates: list[CandidateRecord]
    sections: list[PaperSection]


def _prompt() -> str:
    return (files("arxiv_agent.prompts") / "planner.md").read_text(encoding="utf-8")


def build_planner_agent() -> Agent[PlannerInput, PlannerResult]:
    worker = build_worker_agent()
    model = AnthropicModel("claude-sonnet-4-6")
    agent: Agent[PlannerInput, PlannerResult] = Agent(
        model=model,
        deps_type=PlannerInput,
        output_type=PlannerResult,
        system_prompt=_prompt(),
    )

    @agent.tool
    async def search_arxiv(ctx: RunContext[PlannerInput], query: str, limit: int = 6) -> list[dict]:
        results = await tools.search_arxiv(query, limit=limit,
                                           date_from=ctx.deps.date_from,
                                           date_to=ctx.deps.date_to)
        return [{"id": r.id, "title": r.title, "abstract": r.abstract,
                 "published": r.published} for r in results]

    @agent.tool
    async def fetch_metadata(ctx: RunContext[PlannerInput], paper_id: str) -> dict:
        m = await tools.fetch_metadata(paper_id)
        return {"id": m.id, "title": m.title, "abstract": m.abstract,
                "authors": list(m.authors), "published": m.published}

    @agent.tool
    async def score_candidate(ctx: RunContext[PlannerInput],
                              metadata_id: str) -> dict:
        s = await tools.score_candidate(metadata_id, ctx.deps.research_interest)
        return {"paper_id": s.paper_id, "score": s.score, "rationale": s.rationale}

    @agent.tool
    async def dispatch_worker(ctx: RunContext[PlannerInput], paper_id: str) -> dict:
        worker_deps = WorkerInput(
            paper_id=paper_id,
            research_interest=ctx.deps.research_interest,
        )
        worker_prompt = (
            f"Deep-read paper {paper_id} for research interest: "
            f"{ctx.deps.research_interest}. Return the WorkerResult."
        )
        res = await worker.run(worker_prompt, deps=worker_deps)
        return {"paper_id": res.output.paper_id, "summary": res.output.summary}

    @agent.tool
    async def compose_digest(ctx: RunContext[PlannerInput],
                             sections: list[dict]) -> str:
        from .tools import Summary
        summaries = [Summary(paper_id=s["paper_id"], text=s["summary"]) for s in sections]
        return await tools.compose_digest(summaries, ctx.deps.research_interest)

    return agent
