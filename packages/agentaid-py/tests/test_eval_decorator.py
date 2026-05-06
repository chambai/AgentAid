import pytest
from agentaid.eval import eval as agentaid_eval, registry
from agentaid.models import EvalMode, EvalResult, Run, Golden
from datetime import datetime

@pytest.mark.asyncio
async def test_decorator_registers_and_invokes() -> None:
    @agentaid_eval(name="t_sum_present", mode=EvalMode.INVARIANT)
    async def my_eval(run: Run, golden: Golden | None = None) -> EvalResult:
        ok = bool(run.output and "summary" in (run.output or {}))
        return EvalResult(run_id=run.id, eval_name="t_sum_present",
                          mode=EvalMode.INVARIANT, score=1.0 if ok else 0.0)

    assert "t_sum_present" in registry.list_evals()
    spec = registry.get_eval("t_sum_present")
    run = Run(id="r", agent_name="a", started_at=datetime.utcnow(),
              output={"summary": "x"})
    result = await spec.fn(run, None)
    assert result.score == 1.0

def test_duplicate_registration_raises() -> None:
    @agentaid_eval(name="t_sum_present", mode=EvalMode.INVARIANT)
    async def first(run: Run, golden: Golden | None = None) -> EvalResult:
        return EvalResult(run_id=run.id, eval_name="t_sum_present",
                          mode=EvalMode.INVARIANT, score=1.0)
    with pytest.raises(ValueError):
        @agentaid_eval(name="t_sum_present", mode=EvalMode.INVARIANT)
        async def dup(run: Run, golden: Golden | None = None) -> EvalResult:
            raise NotImplementedError
