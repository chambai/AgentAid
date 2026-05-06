import pytest

@pytest.mark.live
def test_real_arxiv_search_returns_at_least_one_result() -> None:
    from arxiv_agent.mock_arxiv.real import RealArxivClient
    c = RealArxivClient()
    results = c.search("concept drift", limit=2)
    assert results
    assert results[0].title

def test_get_arxiv_client_returns_real_when_flag_set(monkeypatch) -> None:
    monkeypatch.setenv("AGENTAID_USE_REAL_ARXIV", "1")
    # Reload `client` so the env-var gate is rechecked.
    import importlib, arxiv_agent.mock_arxiv.client as cli
    importlib.reload(cli)
    from arxiv_agent.mock_arxiv.real import RealArxivClient
    assert isinstance(cli.get_arxiv_client(), RealArxivClient)

def test_get_arxiv_client_returns_mock_by_default(monkeypatch) -> None:
    monkeypatch.delenv("AGENTAID_USE_REAL_ARXIV", raising=False)
    import importlib, arxiv_agent.mock_arxiv.client as cli
    importlib.reload(cli)
    from arxiv_agent.mock_arxiv.client import MockArxivClient
    assert isinstance(cli.get_arxiv_client(), MockArxivClient)
