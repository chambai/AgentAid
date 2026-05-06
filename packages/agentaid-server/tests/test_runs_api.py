import pytest
from datetime import datetime
from httpx import AsyncClient, ASGITransport

@pytest.fixture
async def app_with_data(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTAID_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'r.db'}")
    import importlib, agentaid_server.config as cfg, agentaid_server.db.engine as eng, agentaid_server.main as mn
    importlib.reload(cfg); importlib.reload(eng); importlib.reload(mn)
    from agentaid_server.db.engine import SessionLocal, init_db
    from agentaid_server.db.models import Run, Span
    await init_db()
    async with SessionLocal() as s:
        s.add(Run(id="run-A", agent_name="arxiv-planner",
                  started_at=datetime(2026,5,6,10), ended_at=datetime(2026,5,6,10,5),
                  status="succeeded"))
        s.add(Span(id="span-A1", run_id="run-A", parent_span_id=None, name="planner",
                   role="planner", started_at=datetime(2026,5,6,10),
                   ended_at=datetime(2026,5,6,10,5), attributes={}, events=[]))
        await s.commit()
    return mn.app

@pytest.mark.asyncio
async def test_list_runs(app_with_data) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_with_data), base_url="http://t") as c:
        r = await c.get("/runs")
    assert r.status_code == 200
    body = r.json()
    assert any(run["id"] == "run-A" for run in body["runs"])

@pytest.mark.asyncio
async def test_get_run_with_spans(app_with_data) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_with_data), base_url="http://t") as c:
        r = await c.get("/runs/run-A")
    assert r.status_code == 200
    body = r.json()
    assert body["run"]["id"] == "run-A"
    assert any(s["id"] == "span-A1" for s in body["spans"])
