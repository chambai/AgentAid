from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid

from agentaid.otel import install as install_otel
from agentaid.otel.conventions import AgentAid
from opentelemetry import trace
from opentelemetry.trace import StatusCode

from . import tools as agent_tools
from .planner import PlannerInput, build_planner_agent, figures_ctx


async def _main(research_interest: str, date_from: str, date_to: str) -> None:
    install_otel()
    tracer = trace.get_tracer("arxiv_agent.cli")
    run_id = os.environ.get("AGENTAID_RUN_ID") or f"live-{uuid.uuid4().hex[:10]}"

    with tracer.start_as_current_span("arxiv_agent.run") as root:
        root.set_attribute(AgentAid.RUN_ID, run_id)
        root.set_attribute(AgentAid.AGENT_NAME, "arxiv-planner")
        root.set_attribute(AgentAid.ROLE, "planner")
        root.set_attribute(
            AgentAid.INPUT,
            json.dumps({
                "research_interest": research_interest,
                "date_from": date_from,
                "date_to": date_to,
            }),
        )

        agent = build_planner_agent()
        deps = PlannerInput(
            research_interest=research_interest,
            date_from=date_from, date_to=date_to,
        )
        user_prompt = (
            f"Research interest: {research_interest}\n"
            f"Date window: {date_from} to {date_to}\n"
            "Produce the digest now."
        )
        # Reset both figure side-channels for this run. The contextvar in
        # planner.py records what the LLM threaded through PlannerResult /
        # WorkerResult; agent_tools.reset_run_figures() clears the
        # lower-level side-channel that captures figures the moment
        # tools.extract_figures() runs (the reliable path — bypasses the
        # LLM entirely).
        figures_token = figures_ctx.set({})
        agent_tools.reset_run_figures()
        try:
            try:
                res = await agent.run(user_prompt, deps=deps)
            except Exception as exc:
                # Mark the run as failed so the digest endpoint and consumer
                # UI can stop polling and surface a clear error rather than
                # spin forever.
                root.set_attribute(
                    AgentAid.OUTPUT,
                    json.dumps({
                        "digest": "",
                        "candidates": [],
                        "sections": [],
                        "figures": {},
                        "error": f"{type(exc).__name__}: {exc}",
                    }),
                )
                root.set_status(StatusCode.ERROR, str(exc))
                print(json.dumps({"run_id": run_id, "error": str(exc)}, indent=2),
                      file=sys.stderr)
                raise SystemExit(1)

            # Merge from three sources, in increasing-trust order:
            #   1. LLM-populated PlannerResult.figures (often empty)
            #   2. planner-level contextvar populated from dispatch_worker
            #      using WorkerResult.figure_descriptions (also LLM-driven,
            #      also unreliable)
            #   3. tools-level side-channel populated when tools.extract_figures
            #      actually fires (deterministic — no LLM trust required)
            # Source #3 wins on duplicate paper_ids because it carries the
            # actual filename pulled from the mock arXiv corpus rather than a
            # potentially-paraphrased LLM rendition.
            llm_figures = {
                pid: [f.model_dump() for f in figs]
                for pid, figs in res.output.figures.items()
            }
            ctx_figures = figures_ctx.get()
            tool_figures = agent_tools.get_run_figures()
            merged_figures = {**llm_figures, **ctx_figures, **tool_figures}

            root.set_attribute(
                AgentAid.OUTPUT,
                json.dumps({
                    "digest": res.output.digest,
                    "candidates": [c.model_dump() for c in res.output.candidates],
                    "sections": [s.model_dump() for s in res.output.sections],
                    "figures": merged_figures,
                }),
            )
        finally:
            figures_ctx.reset(figures_token)

    print(json.dumps({
        "run_id": run_id,
        "digest": res.output.digest,
        "candidates": [c.model_dump() for c in res.output.candidates],
    }, indent=2))


if __name__ == "__main__":
    interest = sys.argv[1] if len(sys.argv) > 1 else "concept drift detection in streaming ML"
    df = sys.argv[2] if len(sys.argv) > 2 else "2024-01-01"
    dt = sys.argv[3] if len(sys.argv) > 3 else "2024-12-31"
    asyncio.run(_main(interest, df, dt))
