from __future__ import annotations
import time
from urllib.parse import urlencode
import httpx
import feedparser
from .mock import PaperSummary, Paper, Figure

ARXIV_API = "http://export.arxiv.org/api/query"

class RealArxivClient:
    """Real arXiv client. Polite by default: 3-second delay between requests,
    in-process call cache. Falls back to mock figure data — extracting figures
    from arXiv PDFs is out of scope for this iteration.
    """
    def __init__(self, min_delay_s: float = 3.0, timeout_s: float = 15.0) -> None:
        self.min_delay = min_delay_s
        self._last_call = 0.0
        self._client = httpx.Client(
            timeout=timeout_s,
            headers={"User-Agent": "AgentAid/0.0 (portfolio project)"},
        )
        self._query_cache: dict[tuple[tuple[str, str], ...], str] = {}
        # Reuse mock figures so the multi-modal pipeline still has data when
        # the real API is in use.
        from .mock import MockArxivCore
        self._fallback = MockArxivCore()

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self._last_call = time.monotonic()

    def _query(self, params_tuple: tuple[tuple[str, str], ...]) -> str:
        if params_tuple in self._query_cache:
            return self._query_cache[params_tuple]
        self._wait()
        url = ARXIV_API + "?" + urlencode(dict(params_tuple))
        r = self._client.get(url)
        r.raise_for_status()
        self._query_cache[params_tuple] = r.text
        return r.text

    def search(self, query: str, limit: int = 10,
               date_from: str | None = None, date_to: str | None = None) -> list[PaperSummary]:
        params = (
            ("search_query", f"all:{query}"),
            ("start", "0"),
            ("max_results", str(limit)),
            ("sortBy", "submittedDate"),
            ("sortOrder", "descending"),
        )
        raw = self._query(params)
        feed = feedparser.parse(raw)
        out: list[PaperSummary] = []
        for entry in feed.entries[:limit]:
            published = entry.get("published", "")[:10]
            if date_from and published < date_from:
                continue
            if date_to and published > date_to:
                continue
            out.append(PaperSummary(
                id=entry.get("id", "").rsplit("/", 1)[-1].replace("v1", ""),
                title=entry.get("title", "").strip(),
                authors=tuple(a.get("name", "") for a in entry.get("authors", [])),
                abstract=entry.get("summary", "").strip(),
                published=published,
                categories=tuple(t.get("term", "") for t in entry.get("tags", [])),
            ))
        return out

    def fetch_metadata(self, paper_id: str) -> PaperSummary:
        raw = self._query((("id_list", paper_id),))
        feed = feedparser.parse(raw)
        if not feed.entries:
            return self._fallback.fetch_metadata(paper_id)
        e = feed.entries[0]
        return PaperSummary(
            id=paper_id,
            title=e.get("title", "").strip(),
            authors=tuple(a.get("name", "") for a in e.get("authors", [])),
            abstract=e.get("summary", "").strip(),
            published=e.get("published", "")[:10],
            categories=tuple(t.get("term", "") for t in e.get("tags", [])),
        )

    def fetch_paper(self, paper_id: str) -> Paper:
        # Full text via PDF parsing is out of scope; return abstract as body.
        meta = self.fetch_metadata(paper_id)
        return Paper(
            id=meta.id, title=meta.title, authors=meta.authors,
            abstract=meta.abstract, published=meta.published,
            categories=meta.categories,
            body=meta.abstract,
        )

    def extract_figures(self, paper_id: str) -> list[Figure]:
        return self._fallback.extract_figures(paper_id)
