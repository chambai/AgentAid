from __future__ import annotations

import asyncio
import json
import sys
import uuid

from agentaid.otel import install as install_otel
from agentaid.otel.conventions import AgentAid
from opentelemetry import trace

from .planner import PlannerInput, build_planner_agent


async def _main(research_interest: str, date_from: str, date_to: str) -> None:
    install_otel()
    tracer = trace.get_tracer("arxiv_agent.cli")
    run_id = f"live-{uuid.uuid4().hex[:10]}"

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
        res = await agent.run(user_prompt, deps=deps)

        root.set_attribute(
            AgentAid.OUTPUT,
            json.dumps({
                "digest": res.output.digest,
                "sections": [s.model_dump() for s in res.output.sections],
            }),
        )

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
