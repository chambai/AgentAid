from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def app_with_digest(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTAID_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'d.db'}")
    import importlib

    import agentaid_server.config as cfg
    import agentaid_server.db.engine as eng
    import agentaid_server.main as mn
    importlib.reload(cfg)
    importlib.reload(eng)
    importlib.reload(mn)
    from agentaid_server.db.engine import SessionLocal, init_db
    from agentaid_server.db.models import Run
    await init_db()
    async with SessionLocal() as s:
        s.add(Run(
            id="digest-test-1",
            agent_name="arxiv-planner",
            started_at=datetime(2026, 5, 6, 10),
            ended_at=datetime(2026, 5, 6, 10, 5),
            status="succeeded",
            input={
                "research_interest": "concept drift",
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
            },
            output={
                "digest": "## hi\n- thing",
                "candidates": [{"paper_id": "x", "title": "X", "score": 0.9, "rationale": "r"}],
                "sections": [],
            },
        ))
        s.add(Run(
            id="no-digest-run",
            agent_name="arxiv-planner",
            started_at=datetime(2026, 5, 5, 10),
            ended_at=datetime(2026, 5, 5, 10, 5),
            status="succeeded",
            input={"research_interest": "other"},
            output=None,
        ))
        await s.commit()
    return mn.app


@pytest.mark.asyncio
async def test_list_digests(app_with_digest) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_with_digest), base_url="http://t") as c:
        r = await c.get("/digests")
    assert r.status_code == 200
    body = r.json()
    ids = [d["run_id"] for d in body["digests"]]
    assert "digest-test-1" in ids
    assert "no-digest-run" not in ids
    row = next(d for d in body["digests"] if d["run_id"] == "digest-test-1")
    assert row["top_paper_title"] == "X"
    assert row["research_interest"] == "concept drift"


@pytest.mark.asyncio
async def test_get_digest(app_with_digest) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_with_digest), base_url="http://t") as c:
        r = await c.get("/digests/digest-test-1")
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == "digest-test-1"
    assert body["digest"] == "## hi\n- thing"
    assert len(body["candidates"]) == 1
    assert body["candidates"][0]["title"] == "X"
    assert body["sections"] == []


@pytest.mark.asyncio
async def test_get_digest_not_found(app_with_digest) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_with_digest), base_url="http://t") as c:
        r = await c.get("/digests/no-such-run")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_digest_no_digest_output(app_with_digest) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_with_digest), base_url="http://t") as c:
        r = await c.get("/digests/no-digest-run")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /digests tests
# ---------------------------------------------------------------------------

@pytest.fixture
async def app_for_post(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTAID_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'p.db'}")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    import importlib

    import agentaid_server.config as cfg
    import agentaid_server.db.engine as eng
    import agentaid_server.main as mn
    importlib.reload(cfg)
    importlib.reload(eng)
    importlib.reload(mn)
    from agentaid_server.db.engine import init_db
    await init_db()
    return mn.app


@pytest.mark.asyncio
async def test_post_digest_creates_run(app_for_post) -> None:
    """POST /digests stubs the subprocess, returns 202, and creates a running row."""
    fake_proc = MagicMock()
    fake_proc.wait = AsyncMock(return_value=0)

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=fake_proc)):
        async with AsyncClient(transport=ASGITransport(app=app_for_post), base_url="http://t") as c:
            r = await c.post("/digests", json={
                "research_interest": "concept drift in streaming ML",
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
            })

    assert r.status_code == 202
    body = r.json()
    assert "run_id" in body
    assert body["run_id"].startswith("live-")
    assert body["status"] == "running"

    # Verify the placeholder row was committed
    from agentaid_server.db.engine import SessionLocal
    from agentaid_server.db.models import Run
    from sqlmodel import select

    async with SessionLocal() as s:
        run = (await s.exec(select(Run).where(Run.id == body["run_id"]))).first()
    assert run is not None
    assert run.status == "running"
    assert run.input["research_interest"] == "concept drift in streaming ML"


@pytest.mark.asyncio
async def test_post_digest_empty_interest_returns_422(app_for_post) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_for_post), base_url="http://t") as c:
        r = await c.post("/digests", json={
            "research_interest": "",
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_post_digest_missing_field_returns_422(app_for_post) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_for_post), base_url="http://t") as c:
        r = await c.post("/digests", json={
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_post_digest_no_api_key_returns_503(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTAID_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'n.db'}")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import importlib

    import agentaid_server.config as cfg
    import agentaid_server.db.engine as eng
    import agentaid_server.main as mn
    importlib.reload(cfg)
    importlib.reload(eng)
    importlib.reload(mn)
    from agentaid_server.db.engine import init_db
    await init_db()

    async with AsyncClient(transport=ASGITransport(app=mn.app), base_url="http://t") as c:
        r = await c.post("/digests", json={
            "research_interest": "test",
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        })
    assert r.status_code == 503
