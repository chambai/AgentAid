import pytest
from arxiv_agent.worker import WorkerInput, WorkerResult, build_worker_agent


@pytest.mark.live
async def test_worker_processes_known_paper() -> None:
    agent = build_worker_agent()
    res = await agent.run(WorkerInput(
        paper_id="2401.00001",
        research_interest="concept drift detection in streaming ML",
    ))
    assert isinstance(res.output, WorkerResult)
    assert res.output.paper_id == "2401.00001"
    assert res.output.summary
    assert len(res.output.figure_descriptions) >= 1

def test_worker_input_model_validates() -> None:
    with pytest.raises(ValueError):
        WorkerInput(paper_id="", research_interest="x")
