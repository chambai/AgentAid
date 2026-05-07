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
        # Set a fresh dict in the contextvar so dispatch_worker calls inside
        # this run accumulate into it. Critical: ContextVar defaults are
        # evaluated once at module import; without a per-run set() the same
        # dict would be shared across runs.
        figures_token = figures_ctx.set({})
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

            # Merge LLM-populated figures (best-effort) with the side-channel
            # accumulator (deterministic). The side channel wins on duplicate
            # paper ids — it has the actual filenames, the LLM may have
            # paraphrased.
            llm_figures = {
                pid: [f.model_dump() for f in figs]
                for pid, figs in res.output.figures.items()
            }
            captured_figures = figures_ctx.get()
            merged_figures = {**llm_figures, **captured_figures}

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
