import pytest
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from sqlmodel import select
from agentaid_server.db.models import Run, Span

def _ns(dt: datetime) -> int:
    return int(dt.timestamp() * 1e9)

@pytest.mark.asyncio
async def test_ingest_creates_run_and_spans(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTAID_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    import importlib, agentaid_server.config as cfg, agentaid_server.db.engine as eng, agentaid_server.main as mn
    importlib.reload(cfg); importlib.reload(eng); importlib.reload(mn)
    from agentaid_server.main import app as fresh_app
    from agentaid_server.db.engine import SessionLocal, init_db
    await init_db()

    payload = {
        "spans": [
            {
                "trace_id": "0" * 32, "span_id": "1" * 16, "parent_span_id": None,
                "name": "planner", "kind": "INTERNAL",
                "start_time_unix_nano": _ns(datetime(2026, 5, 6, 12, 0, 0)),
                "end_time_unix_nano":   _ns(datetime(2026, 5, 6, 12, 0, 5)),
                "attributes": {"agentaid.run_id": "run-001",
                               "agentaid.role": "planner",
                               "agentaid.agent_name": "arxiv-planner",
                               "agentaid.input": '{"research_interest":"x"}'},
                "events": [], "status": {"code": "OK", "description": ""},
            },
            {
                "trace_id": "0" * 32, "span_id": "2" * 16, "parent_span_id": "1" * 16,
                "name": "worker", "kind": "INTERNAL",
                "start_time_unix_nano": _ns(datetime(2026, 5, 6, 12, 0, 1)),
                "end_time_unix_nano":   _ns(datetime(2026, 5, 6, 12, 0, 4)),
                "attributes": {"agentaid.run_id": "run-001",
                               "agentaid.role": "worker"},
                "events": [], "status": {"code": "OK", "description": ""},
            },
        ]
    }

    transport = ASGITransport(app=fresh_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/ingest", json=payload)
    assert r.status_code == 202

    async with SessionLocal() as s:
        run = (await s.exec(select(Run).where(Run.id == "run-001"))).first()
        spans = (await s.exec(select(Span).where(Span.run_id == "run-001"))).all()
    assert run is not None
    assert run.agent_name == "arxiv-planner"
    assert len(spans) == 2
