from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

_FIGURES_DIR = str(
    Path(__file__).parents[3]
    / "reference-agent/src/arxiv_agent/mock_arxiv/data/figures"
)


@pytest.fixture
async def figures_app(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTAID_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'f.db'}")
    monkeypatch.setenv("AGENTAID_FIGURES_DIR", _FIGURES_DIR)
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
async def test_get_figure_returns_jpeg(figures_app) -> None:
    async with AsyncClient(transport=ASGITransport(app=figures_app), base_url="http://t") as c:
        r = await c.get("/papers/2401.00001/figures/fig_2401_00001_1.jpg")
    assert r.status_code == 200
    assert "image/jpeg" in r.headers["content-type"]
    # JPEG magic bytes
    assert r.content[:3] == b"\xff\xd8\xff"


@pytest.mark.asyncio
async def test_get_figure_not_found(figures_app) -> None:
    async with AsyncClient(transport=ASGITransport(app=figures_app), base_url="http://t") as c:
        r = await c.get("/papers/9999.99999/figures/no_such_file.jpg")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_path_traversal_rejected(figures_app) -> None:
    async with AsyncClient(transport=ASGITransport(app=figures_app), base_url="http://t") as c:
        # httpx will URL-encode the path; test the encoded form as well
        r = await c.get("/papers/x/figures/..%2F..%2Fetc%2Fpasswd")
    # Must be 4xx, and must NOT return /etc/passwd contents
    assert r.status_code >= 400
    assert b"root" not in r.content


@pytest.mark.asyncio
async def test_path_traversal_dotdot_rejected(figures_app) -> None:
    """Direct '..' in filename segment is rejected."""
    async with AsyncClient(transport=ASGITransport(app=figures_app), base_url="http://t") as c:
        r = await c.get("/papers/x/figures/..%2Fetc%2Fpasswd")
    assert r.status_code >= 400
    assert b"root" not in r.content
