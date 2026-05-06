import pytest
from httpx import AsyncClient, ASGITransport
from agentaid_server.main import app

@pytest.mark.asyncio
async def test_healthcheck_responds_ok() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_db_tables_exist_on_startup(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "agentaid_test.sqlite"
    monkeypatch.setenv("AGENTAID_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    import importlib, agentaid_server.config as cfg, agentaid_server.db.engine as eng
    importlib.reload(cfg); importlib.reload(eng)
    from agentaid_server.db.engine import init_db
    await init_db()
    import sqlite3
    conn = sqlite3.connect(db_path)
    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"run", "span", "evalresult", "driftstaterow", "dataset",
            "datasetrow", "regressionrun"} <= names
