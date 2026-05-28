from __future__ import annotations

import os

from .mock import Figure, MockArxivCore, Paper, PaperSummary


class MockArxivClient:
    """Default arXiv client for development. Real API switched in by Task 29."""

    def __init__(self) -> None:
        self._core = MockArxivCore()

    def search(
        self,
        query: str,
        limit: int = 10,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[PaperSummary]:
        return self._core.search(query, limit, date_from, date_to)

    def fetch_metadata(self, paper_id: str) -> PaperSummary:
        return self._core.fetch_metadata(paper_id)

    def fetch_paper(self, paper_id: str) -> Paper:
        return self._core.fetch_paper(paper_id)

    def extract_figures(self, paper_id: str) -> list[Figure]:
        return self._core.extract_figures(paper_id)


def get_arxiv_client() -> MockArxivClient:
    """Factory used by tools.py. Real implementation wired in Task 29."""
    if os.getenv("AGENTAID_USE_REAL_ARXIV"):
        from .real import RealArxivClient  # type: ignore[import-not-found]

        return RealArxivClient()  # type: ignore[return-value]
    return MockArxivClient()
