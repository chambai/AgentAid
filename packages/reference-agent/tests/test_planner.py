import pytest
from arxiv_agent.planner import PlannerInput, PlannerResult, build_planner_agent


def test_planner_input_validates() -> None:
    PlannerInput(research_interest="concept drift", date_from="2024-01-01", date_to="2024-12-31")
    with pytest.raises(ValueError):
        PlannerInput(research_interest="", date_from="2024-01-01", date_to="2024-12-31")

@pytest.mark.live
async def test_planner_produces_digest_for_drift_interest() -> None:
    agent = build_planner_agent()
    res = await agent.run(PlannerInput(
        research_interest="concept drift detection in streaming ML",
        date_from="2024-01-01", date_to="2024-12-31",
    ))
    assert isinstance(res.output, PlannerResult)
    assert "##" in res.output.digest
    assert len(res.output.candidates) >= 3
    assert res.output.candidates[0].score >= 0.0
