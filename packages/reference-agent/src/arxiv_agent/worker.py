from __future__ import annotations

from importlib.resources import files

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel

from . import tools


class WorkerInput(BaseModel):
    paper_id: str = Field(min_length=1)
    research_interest: str = Field(min_length=1)
    follow_up_question: str | None = None


class FigureDescription(BaseModel):
    caption: str
    description: str


class WorkerResult(BaseModel):
    paper_id: str
    summary: str
    figure_descriptions: list[FigureDescription]
    follow_up_answer: str | None = None


def _prompt() -> str:
    return (files("arxiv_agent.prompts") / "worker.md").read_text(encoding="utf-8")


def build_worker_agent() -> Agent[WorkerInput, WorkerResult]:
    model = AnthropicModel("claude-sonnet-4-6")
    agent: Agent[WorkerInput, WorkerResult] = Agent(
        model=model,
        deps_type=WorkerInput,
        output_type=WorkerResult,
        system_prompt=_prompt(),
    )

    @agent.tool
    async def fetch_paper(ctx: RunContext[WorkerInput], paper_id: str) -> str:
        p = await tools.fetch_paper(paper_id)
        return p.body

    @agent.tool
    async def extract_figures(ctx: RunContext[WorkerInput], paper_id: str) -> list[dict]:
        descs = await tools.extract_figures(paper_id)
        return [{"caption": d.caption, "description": d.description} for d in descs]

    @agent.tool
    async def summarize(ctx: RunContext[WorkerInput], paper_id: str, focus: str) -> str:
        s = await tools.summarize(paper_id, focus)
        return s.text

    @agent.tool
    async def query_paper(ctx: RunContext[WorkerInput], paper_id: str, question: str) -> str:
        return await tools.query_paper(paper_id, question)

    @agent.system_prompt
    def _annotate_role(ctx: RunContext[WorkerInput]) -> str:
        from opentelemetry import trace
        span = trace.get_current_span()
        span.set_attribute("agentaid.role", "worker")
        span.set_attribute("agentaid.agent_name", "arxiv-worker")
        return ""

    return agent
