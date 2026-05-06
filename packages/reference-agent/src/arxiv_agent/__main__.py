from __future__ import annotations
import asyncio
import json
import sys
from agentaid.otel import install as install_otel
from .planner import build_planner_agent, PlannerInput


async def _main(research_interest: str, date_from: str, date_to: str) -> None:
    install_otel()
    agent = build_planner_agent()
    res = await agent.run(PlannerInput(
        research_interest=research_interest,
        date_from=date_from, date_to=date_to,
    ))
    print(json.dumps({
        "digest": res.output.digest,
        "candidates": [c.model_dump() for c in res.output.candidates],
    }, indent=2))


if __name__ == "__main__":
    interest = sys.argv[1] if len(sys.argv) > 1 else "concept drift detection in streaming ML"
    df = sys.argv[2] if len(sys.argv) > 2 else "2024-01-01"
    dt = sys.argv[3] if len(sys.argv) > 3 else "2024-12-31"
    asyncio.run(_main(interest, df, dt))
