# AgentAid Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build AgentAid — a drift-aware observability and evaluation platform for production AI agents — with a multi-agent (planner+worker) arXiv research assistant as the reference workload, in ~88h of CC-augmented work spread across 7–8 days.

**Architecture:** Three layers. (1) Agent + SDK layer: Pydantic AI reference agent and a bare-Anthropic-SDK example, both emitting OTel/GenAI spans via Python and TypeScript SDKs. (2) Server layer: FastAPI app ingesting otel/genai, storing in SQLite via SQLModel, running async LLM-judge evals and three drift-detector workers (ADWIN/MMD/PSI). (3) Frontend layer: Vite + React + TS, drift-first home, Gantt trace detail, summary-led run comparison, drift detail pages.

**Tech Stack:** Python 3.12 · Pydantic v2 · Pydantic AI · FastAPI · SQLModel/SQLAlchemy 2.0 (async) · SQLite · `uv` workspaces · TypeScript 5 · Vite · React 19 · TanStack Query · React Router 6 · pnpm workspaces · Anthropic SDK · OpenTelemetry (OTel/GenAI semantic conventions) · pytest · vitest · ruff · eslint.

**Reference spec:** `docs/superpowers/specs/2026-05-06-agentaid-design.md`. Read it before starting Task 1.

## Conventions

- **Commits:** Terse, imperative, lowercase subject, under 72 chars, body only when subject doesn't say enough. No `🤖 Generated with Claude Code` lines and no `Co-Authored-By` trailers (per project CLAUDE.md).
- **Issue tracking:** This project uses `bd` (beads). Open a bd issue per task as you start it (`bd create --title="..." --type=task --priority=2`), claim it (`bd update <id> --claim`), close on completion (`bd close <id>`).
- **TDD discipline:** Where the task implements logic, write the failing test first, run it to confirm it fails, implement, run it to confirm it passes, commit. Where the task is scaffolding/config, the "test" is a smoke check (build runs, server starts, page renders).
- **One commit per task** unless the task explicitly splits.
- **Anthropic API key:** export `ANTHROPIC_API_KEY` before starting Task 4 (the first task that calls a model). Use `claude-haiku-4-5` for cheap dev iteration; `claude-sonnet-4-6` for evals where quality matters.
- **Python tooling:** `uv` everywhere. `uv add <pkg>` to add deps, `uv run <cmd>` to run inside a workspace member.
- **TS tooling:** `pnpm` everywhere. `pnpm --filter <pkg> add <dep>` for adding deps, `pnpm --filter <pkg> dev` to run.
- **Type checking:** mypy strict for Python, `tsc --strict --noEmit` for TS. Both run in CI (Task 30) but you should run them locally as you go.

## File Structure (locked at plan-time)

```
agentaid/
├── README.md                           # Task 31
├── Makefile                            # Task 1 (top-level dev commands)
├── pyproject.toml                      # Task 1 (uv workspace root)
├── package.json                        # Task 1 (pnpm workspace root)
├── pnpm-workspace.yaml                 # Task 1
├── uv.lock                             # Task 1 (gitignored? no, commit it)
├── .github/workflows/ci.yml            # Task 30
├── docs/superpowers/                   # already exists
├── eval/golden/dataset.json            # Task 5
├── scripts/
│   ├── seed_drift.py                   # Task 22
│   └── run_demo.py                     # Task 32
├── packages/
│   ├── agentaid-py/                    # Tasks 6, 7, 15, 16, 19, 20
│   │   ├── pyproject.toml
│   │   └── src/agentaid/
│   │       ├── __init__.py
│   │       ├── models.py               # Run, Span, EvalResult, Golden, DriftState (Pydantic)
│   │       ├── otel/exporter.py        # OTel/GenAI HTTP exporter
│   │       ├── otel/conventions.py     # GenAI attribute helpers
│   │       ├── eval/
│   │       │   ├── decorator.py        # @agentaid.eval
│   │       │   ├── registry.py
│   │       │   ├── judge.py            # llm_judge helper
│   │       │   └── templates/
│   │       │       ├── relevance_judge.py
│   │       │       ├── faithfulness_judge.py
│   │       │       ├── structural_completeness.py
│   │       │       └── cost_within_budget.py
│   │       └── drift/
│   │           ├── protocol.py
│   │           ├── adwin.py
│   │           ├── mmd.py
│   │           └── psi.py
│   ├── agentaid-ts/                    # Task 27
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── src/
│   │       ├── index.ts
│   │       ├── otel/exporter.ts
│   │       ├── otel/conventions.ts
│   │       ├── eval/define.ts
│   │       ├── eval/models.ts
│   │       └── eval/invariants.ts
│   ├── agentaid-server/                # Tasks 9–11, 17, 21, 24
│   │   ├── pyproject.toml
│   │   └── src/agentaid_server/
│   │       ├── __init__.py
│   │       ├── main.py                 # FastAPI app entry
│   │       ├── config.py
│   │       ├── db/engine.py
│   │       ├── db/models.py            # SQLModel: Run, Span, EvalResult, DriftState, Dataset, RegressionRun
│   │       ├── api/ingest.py
│   │       ├── api/runs.py
│   │       ├── api/evals.py
│   │       ├── api/drift.py
│   │       ├── api/datasets.py
│   │       ├── api/regression.py
│   │       ├── ingestion/parser.py
│   │       └── orchestrator/
│   │           ├── eval_runner.py
│   │           ├── regression.py
│   │           └── drift_workers.py
│   ├── agentaid-web/                   # Tasks 12–14, 18, 23, 25, 26
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── tsconfig.json
│   │   └── src/
│   │       ├── main.tsx
│   │       ├── App.tsx
│   │       ├── routes/
│   │       │   ├── DriftHome.tsx
│   │       │   ├── TraceDetail.tsx
│   │       │   ├── RunComparison.tsx
│   │       │   ├── DriftDetail.tsx
│   │       │   ├── EvalResults.tsx
│   │       │   ├── Datasets.tsx
│   │       │   └── RunList.tsx
│   │       ├── components/
│   │       │   ├── GanttChart.tsx
│   │       │   ├── DriftSignalCard.tsx
│   │       │   └── ScoreCard.tsx
│   │       └── api/
│   │           ├── client.ts
│   │           └── types.ts
│   ├── reference-agent/                # Tasks 2–5, 8, 29
│   │   ├── pyproject.toml
│   │   └── src/arxiv_agent/
│   │       ├── __init__.py
│   │       ├── tools.py
│   │       ├── worker.py
│   │       ├── planner.py
│   │       ├── prompts/
│   │       │   ├── planner.md
│   │       │   ├── worker.md
│   │       │   └── synthesis.md
│   │       └── mock_arxiv/
│   │           ├── __init__.py
│   │           ├── client.py           # mock-or-real switcher
│   │           ├── mock.py
│   │           ├── real.py             # Task 29
│   │           └── data/               # canned papers + figures
│   └── bare-sdk-example/               # Task 28
│       ├── pyproject.toml
│       └── src/example.py
└── tests/                              # cross-cutting integration tests if any
```

---

## Phase 0 — Workspace Foundation (Day 1, ~2h)

### Task 1: Workspace scaffold

**Goal:** Top-level `uv` Python workspace + `pnpm` TS workspace, Makefile with dev commands, package directories created (empty stubs OK), CI-friendly structure.

**Files:**
- Create: `pyproject.toml` (uv workspace root)
- Create: `package.json` (pnpm workspace root)
- Create: `pnpm-workspace.yaml`
- Create: `Makefile`
- Modify: `.gitignore` (add Python and TS build artifacts)
- Create stub: `packages/agentaid-py/pyproject.toml`
- Create stub: `packages/agentaid-server/pyproject.toml`
- Create stub: `packages/reference-agent/pyproject.toml`
- Create stub: `packages/bare-sdk-example/pyproject.toml`
- Create stub: `packages/agentaid-ts/package.json`
- Create stub: `packages/agentaid-web/package.json`

- [ ] **Step 1: Open bd issue and claim it**

```bash
bd create --title="Task 1: workspace scaffold" --type=task --priority=2 \
  --description="Set up uv + pnpm workspaces and top-level Makefile"
# note the returned id, then:
bd update <id> --claim
```

- [ ] **Step 2: Top-level Python workspace (`pyproject.toml`)**

```toml
[project]
name = "agentaid-workspace"
version = "0.0.0"
requires-python = ">=3.12"

[tool.uv.workspace]
members = ["packages/agentaid-py", "packages/agentaid-server", "packages/reference-agent", "packages/bare-sdk-example"]

[tool.uv]
dev-dependencies = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "ruff>=0.5",
    "mypy>=1.10",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.mypy]
python_version = "3.12"
strict = true
```

- [ ] **Step 3: Top-level TS workspace (`package.json` + `pnpm-workspace.yaml`)**

```json
{
  "name": "agentaid-workspace",
  "private": true,
  "version": "0.0.0",
  "scripts": {
    "dev": "pnpm --filter agentaid-web dev",
    "build": "pnpm -r build",
    "lint": "pnpm -r lint",
    "test": "pnpm -r test",
    "typecheck": "pnpm -r typecheck"
  },
  "devDependencies": {
    "typescript": "^5.6.0",
    "@types/node": "^22"
  }
}
```

```yaml
# pnpm-workspace.yaml
packages:
  - "packages/agentaid-ts"
  - "packages/agentaid-web"
```

- [ ] **Step 4: Per-package stub `pyproject.toml`s**

For `packages/agentaid-py/pyproject.toml`:

```toml
[project]
name = "agentaid"
version = "0.0.0"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.8",
    "anthropic>=0.40",
    "opentelemetry-api>=1.27",
    "opentelemetry-sdk>=1.27",
    "httpx>=0.27",
    "numpy>=2.0",
    "scipy>=1.14",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/agentaid"]
```

For `packages/agentaid-server/pyproject.toml`:

```toml
[project]
name = "agentaid-server"
version = "0.0.0"
requires-python = ">=3.12"
dependencies = [
    "agentaid",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlmodel>=0.0.22",
    "aiosqlite>=0.20",
    "anthropic>=0.40",
    "pydantic-settings>=2.5",
]

[tool.uv.sources]
agentaid = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/agentaid_server"]
```

For `packages/reference-agent/pyproject.toml`:

```toml
[project]
name = "arxiv-agent"
version = "0.0.0"
requires-python = ">=3.12"
dependencies = [
    "agentaid",
    "pydantic-ai>=0.0.13",
    "anthropic>=0.40",
    "httpx>=0.27",
    "feedparser>=6.0",   # for real arXiv API later
]

[tool.uv.sources]
agentaid = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/arxiv_agent"]
```

For `packages/bare-sdk-example/pyproject.toml`:

```toml
[project]
name = "bare-sdk-example"
version = "0.0.0"
requires-python = ">=3.12"
dependencies = [
    "agentaid",
    "anthropic>=0.40",
    "opentelemetry-api>=1.27",
    "opentelemetry-sdk>=1.27",
]

[tool.uv.sources]
agentaid = { workspace = true }
```

- [ ] **Step 5: Per-package stub `package.json`s**

For `packages/agentaid-ts/package.json`:

```json
{
  "name": "agentaid",
  "version": "0.0.0",
  "private": false,
  "type": "module",
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "test": "vitest run",
    "lint": "eslint src",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@opentelemetry/api": "^1.9.0",
    "@opentelemetry/sdk-trace-node": "^1.27.0",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "vitest": "^2.0.0",
    "eslint": "^9.0.0"
  }
}
```

For `packages/agentaid-web/package.json`:

```json
{
  "name": "agentaid-web",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "lint": "eslint src",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^6.27.0",
    "@tanstack/react-query": "^5.59.0",
    "recharts": "^2.13.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.4.0",
    "vitest": "^2.0.0",
    "@testing-library/react": "^16.0.0",
    "jsdom": "^25.0.0",
    "eslint": "^9.0.0"
  }
}
```

- [ ] **Step 6: Top-level Makefile**

```make
.PHONY: install dev test lint typecheck clean server web agent

install:
	uv sync
	pnpm install

dev:
	@echo "Run \`make server\` and \`make web\` in separate terminals."

server:
	uv run uvicorn agentaid_server.main:app --reload --port 8000

web:
	pnpm --filter agentaid-web dev

agent:
	uv run python -m arxiv_agent

test:
	uv run pytest
	pnpm -r test

lint:
	uv run ruff check .
	pnpm -r lint

typecheck:
	uv run mypy packages/agentaid-py/src packages/agentaid-server/src packages/reference-agent/src
	pnpm -r typecheck

clean:
	rm -rf .venv node_modules packages/*/node_modules packages/*/dist packages/*/.venv
```

- [ ] **Step 7: Update `.gitignore`**

Append:

```
# Python
.venv/
__pycache__/
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# TS / Node
node_modules/
packages/*/dist/
packages/*/.turbo/
*.tsbuildinfo

# Local SQLite databases
*.sqlite
*.sqlite-journal
agentaid.db
```

- [ ] **Step 8: Smoke check — install resolves**

Run:
```bash
uv sync
pnpm install
```

Expected: both succeed without errors. `uv sync` should report installing the four Python workspace members; `pnpm install` should report installing TS workspace members.

- [ ] **Step 9: Commit and close bd issue**

```bash
git add -A
git commit -m "scaffold uv + pnpm workspaces and top-level makefile"
bd close <id>
```

---

## Phase 1 — Reference Agent End-to-End with Mocks (Days 1–2, ~22h)

### Task 2: Mock arXiv layer with seed corpus

**Goal:** Deterministic mock arXiv client with a small canned corpus (10 papers, abstracts, full-text excerpts, 1 figure each as small JPEGs). Default for development.

**Files:**
- Create: `packages/reference-agent/src/arxiv_agent/mock_arxiv/__init__.py`
- Create: `packages/reference-agent/src/arxiv_agent/mock_arxiv/mock.py`
- Create: `packages/reference-agent/src/arxiv_agent/mock_arxiv/client.py`
- Create: `packages/reference-agent/src/arxiv_agent/mock_arxiv/data/papers.json`
- Create: `packages/reference-agent/src/arxiv_agent/mock_arxiv/data/figures/*.jpg` (10 placeholder JPEGs)
- Test: `packages/reference-agent/tests/test_mock_arxiv.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 2: mock arxiv client + seed corpus" --type=task --priority=2 \
  --description="Deterministic mock arXiv layer with 10 papers and 1 figure each"
bd update <id> --claim
```

- [ ] **Step 2: Write failing tests**

`packages/reference-agent/tests/test_mock_arxiv.py`:

```python
import pytest
from arxiv_agent.mock_arxiv.client import MockArxivClient

@pytest.fixture
def client() -> MockArxivClient:
    return MockArxivClient()

def test_search_returns_deterministic_results(client: MockArxivClient) -> None:
    a = client.search("concept drift", limit=5)
    b = client.search("concept drift", limit=5)
    assert [p.id for p in a] == [p.id for p in b]
    assert 1 <= len(a) <= 5

def test_search_filters_by_date_range(client: MockArxivClient) -> None:
    results = client.search("streaming", date_from="2024-01-01", date_to="2024-12-31")
    for p in results:
        assert "2024" in p.published

def test_fetch_metadata_returns_known_paper(client: MockArxivClient) -> None:
    meta = client.fetch_metadata("2401.00001")
    assert meta.id == "2401.00001"
    assert meta.title
    assert meta.abstract

def test_fetch_paper_returns_text_excerpt(client: MockArxivClient) -> None:
    paper = client.fetch_paper("2401.00001")
    assert paper.body
    assert len(paper.body) > 200

def test_extract_figures_returns_jpeg_bytes(client: MockArxivClient) -> None:
    figs = client.extract_figures("2401.00001")
    assert len(figs) >= 1
    assert figs[0].content_type == "image/jpeg"
    assert figs[0].data.startswith(b"\xff\xd8\xff")  # JPEG magic
```

Run: `uv run pytest packages/reference-agent/tests/test_mock_arxiv.py -v`
Expected: FAIL — module doesn't exist yet.

- [ ] **Step 3: Author seed data**

`packages/reference-agent/src/arxiv_agent/mock_arxiv/data/papers.json`:

```json
[
  {
    "id": "2401.00001",
    "title": "ADWIN-2: Adaptive Windowing for Concept Drift in Streaming Data",
    "authors": ["A. Bifet", "R. Gavaldà"],
    "abstract": "We present ADWIN-2, an extension to the adaptive windowing algorithm...",
    "published": "2024-01-08",
    "categories": ["cs.LG", "stat.ML"],
    "body": "1. Introduction\n\nConcept drift is the phenomenon where the statistical properties of a target variable change over time...\n\n2. Method\n\nADWIN-2 maintains a sliding window of recent values and applies a Hoeffding bound...\n\n3. Experiments\n\nWe evaluate on the SEA, hyperplane, and electricity datasets...",
    "figures": [{"caption": "ADWIN window dynamics", "filename": "fig_2401_00001_1.jpg"}]
  },
  {
    "id": "2402.00012",
    "title": "Page-Hinkley Revisited for Online Eval-Score Drift Detection",
    "authors": ["S. Klinkenberg"],
    "abstract": "We revisit the Page-Hinkley test for change-point detection in evaluation streams...",
    "published": "2024-02-14",
    "categories": ["stat.ML"],
    "body": "1. Introduction\n\nThe Page-Hinkley test computes a cumulative sum of deviations from the mean and triggers when this sum exceeds a threshold...\n\n2. Application to LLM evaluation\n\nWe apply Page-Hinkley to streaming eval scores from production LLM systems...",
    "figures": [{"caption": "PH detection example", "filename": "fig_2402_00012_1.jpg"}]
  }
]
```

(Author 8 more entries following this shape; vary topics across drift, streaming ML, multi-agent, evaluation, RAG. The exact entries are not load-bearing for the agent design — anything plausibly relevant works. Two are sufficient for tests; ten total provides realistic surface for digest generation.)

- [ ] **Step 4: Generate placeholder JPEGs**

```bash
mkdir -p packages/reference-agent/src/arxiv_agent/mock_arxiv/data/figures
uv run python -c "
from PIL import Image, ImageDraw
import os
out = 'packages/reference-agent/src/arxiv_agent/mock_arxiv/data/figures'
for i in range(1, 11):
    img = Image.new('RGB', (640, 480), color=(240, 240, 240))
    d = ImageDraw.Draw(img)
    d.rectangle([100, 100, 540, 380], outline=(80, 80, 200), width=4)
    d.text((110, 110), f'Figure {i} — synthetic placeholder', fill=(40, 40, 40))
    img.save(os.path.join(out, f'fig_synth_{i}.jpg'), 'JPEG')
"
```

(Add `pillow` as a `[project.optional-dependencies.dev]` to `packages/reference-agent/pyproject.toml` if not already present, or just keep it as a one-time generation step.)

For now, also produce specific filenames matching the JSON's `figures.filename` references; rename two:

```bash
cp packages/reference-agent/src/arxiv_agent/mock_arxiv/data/figures/fig_synth_1.jpg \
   packages/reference-agent/src/arxiv_agent/mock_arxiv/data/figures/fig_2401_00001_1.jpg
cp packages/reference-agent/src/arxiv_agent/mock_arxiv/data/figures/fig_synth_2.jpg \
   packages/reference-agent/src/arxiv_agent/mock_arxiv/data/figures/fig_2402_00012_1.jpg
# repeat for the other 8
```

- [ ] **Step 5: Implement domain models + mock client**

`packages/reference-agent/src/arxiv_agent/mock_arxiv/mock.py`:

```python
from __future__ import annotations
import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Iterable

@dataclass(frozen=True)
class PaperSummary:
    id: str
    title: str
    authors: tuple[str, ...]
    abstract: str
    published: str
    categories: tuple[str, ...]

@dataclass(frozen=True)
class Paper(PaperSummary):
    body: str

@dataclass(frozen=True)
class Figure:
    paper_id: str
    caption: str
    content_type: str
    data: bytes

def _load_corpus() -> list[dict]:
    pkg = files("arxiv_agent.mock_arxiv.data")
    return json.loads((pkg / "papers.json").read_text(encoding="utf-8"))

def _figures_dir() -> Path:
    return Path(str(files("arxiv_agent.mock_arxiv.data") / "figures"))

class MockArxivCore:
    def __init__(self) -> None:
        self._corpus = _load_corpus()
        self._by_id = {p["id"]: p for p in self._corpus}

    def search(self, query: str, limit: int = 10,
               date_from: str | None = None, date_to: str | None = None) -> list[PaperSummary]:
        q = query.lower()
        results: list[PaperSummary] = []
        for p in self._corpus:
            if date_from and p["published"] < date_from:
                continue
            if date_to and p["published"] > date_to:
                continue
            blob = (p["title"] + " " + p["abstract"]).lower()
            if any(tok in blob for tok in q.split() if tok):
                results.append(PaperSummary(
                    id=p["id"], title=p["title"],
                    authors=tuple(p["authors"]),
                    abstract=p["abstract"],
                    published=p["published"],
                    categories=tuple(p["categories"]),
                ))
        return results[:limit]

    def fetch_metadata(self, paper_id: str) -> PaperSummary:
        p = self._by_id[paper_id]
        return PaperSummary(
            id=p["id"], title=p["title"], authors=tuple(p["authors"]),
            abstract=p["abstract"], published=p["published"],
            categories=tuple(p["categories"]),
        )

    def fetch_paper(self, paper_id: str) -> Paper:
        p = self._by_id[paper_id]
        return Paper(
            id=p["id"], title=p["title"], authors=tuple(p["authors"]),
            abstract=p["abstract"], published=p["published"],
            categories=tuple(p["categories"]), body=p["body"],
        )

    def extract_figures(self, paper_id: str) -> list[Figure]:
        p = self._by_id[paper_id]
        out: list[Figure] = []
        for f in p.get("figures", []):
            data = (_figures_dir() / f["filename"]).read_bytes()
            out.append(Figure(paper_id=paper_id, caption=f["caption"],
                              content_type="image/jpeg", data=data))
        return out
```

- [ ] **Step 6: Implement mock-or-real switcher**

`packages/reference-agent/src/arxiv_agent/mock_arxiv/client.py`:

```python
from __future__ import annotations
import os
from .mock import MockArxivCore, PaperSummary, Paper, Figure

class MockArxivClient:
    """Default arXiv client for development. Real API switched in by Task 29."""
    def __init__(self) -> None:
        self._core = MockArxivCore()

    def search(self, query: str, limit: int = 10,
               date_from: str | None = None, date_to: str | None = None) -> list[PaperSummary]:
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
        # Implemented in Task 29
        from .real import RealArxivClient
        return RealArxivClient()  # type: ignore[return-value]
    return MockArxivClient()
```

- [ ] **Step 7: Run tests, expect PASS**

```bash
uv run pytest packages/reference-agent/tests/test_mock_arxiv.py -v
```

Expected: 5 tests pass.

- [ ] **Step 8: Commit and close**

```bash
git add packages/reference-agent
git commit -m "add mock arxiv client with 10-paper seed corpus"
bd close <id>
```

---

### Task 3: Tools module (8 tools wired to mock arXiv + LLM helpers)

**Goal:** Implement the 8 tools described in the spec as plain Python async functions, wired to the mock arXiv client. Tools also use a small LLM helper for `score_candidate`, `summarize`, `query_paper`, and `compose_digest`. No Pydantic AI yet — that's Task 4.

**Files:**
- Create: `packages/reference-agent/src/arxiv_agent/tools.py`
- Create: `packages/reference-agent/src/arxiv_agent/llm.py` (Anthropic client wrapper, vision-capable)
- Test: `packages/reference-agent/tests/test_tools.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 3: tools module + LLM helper" --type=task --priority=2 \
  --description="8 tool functions over mock arXiv plus an Anthropic helper with vision"
bd update <id> --claim
```

- [ ] **Step 2: Write failing tests**

`packages/reference-agent/tests/test_tools.py`:

```python
import pytest
from arxiv_agent import tools

@pytest.mark.asyncio
async def test_search_arxiv_returns_summaries() -> None:
    results = await tools.search_arxiv(query="drift", limit=3)
    assert 1 <= len(results) <= 3
    assert results[0].id

@pytest.mark.asyncio
async def test_fetch_metadata() -> None:
    meta = await tools.fetch_metadata("2401.00001")
    assert meta.title

@pytest.mark.asyncio
async def test_fetch_paper_returns_body() -> None:
    paper = await tools.fetch_paper("2401.00001")
    assert len(paper.body) > 100

@pytest.mark.asyncio
async def test_extract_figures_returns_descriptions() -> None:
    descriptions = await tools.extract_figures("2401.00001")
    assert len(descriptions) >= 1
    assert descriptions[0].description

@pytest.mark.asyncio
async def test_score_candidate_returns_float_in_unit_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock the LLM call to a deterministic score.
    async def fake_score(prompt: str) -> str:
        return '{"score": 0.78, "rationale": "highly on-topic"}'
    monkeypatch.setattr("arxiv_agent.tools._llm_json", fake_score)
    s = await tools.score_candidate(metadata_id="2401.00001",
                                    research_interest="concept drift in streaming ML")
    assert 0.0 <= s.score <= 1.0
    assert s.rationale
```

Run: `uv run pytest packages/reference-agent/tests/test_tools.py -v`
Expected: FAIL (module not implemented).

- [ ] **Step 3: Implement LLM helper**

`packages/reference-agent/src/arxiv_agent/llm.py`:

```python
from __future__ import annotations
import base64
import json
import os
from anthropic import AsyncAnthropic
from anthropic.types import MessageParam, TextBlockParam, ImageBlockParam

_client: AsyncAnthropic | None = None

def _get() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic()
    return _client

CHEAP = os.getenv("AGENTAID_CHEAP_MODEL", "claude-haiku-4-5")
QUALITY = os.getenv("AGENTAID_QUALITY_MODEL", "claude-sonnet-4-6")

async def text(prompt: str, *, model: str = CHEAP, system: str | None = None,
               max_tokens: int = 1024) -> str:
    msg = await _get().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system or "",
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")

async def vision(prompt: str, image_bytes: bytes, content_type: str = "image/jpeg",
                 *, model: str = CHEAP, max_tokens: int = 512) -> str:
    image_b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    content: list[TextBlockParam | ImageBlockParam] = [
        {"type": "image", "source": {"type": "base64", "media_type": content_type, "data": image_b64}},
        {"type": "text", "text": prompt},
    ]
    msg = await _get().messages.create(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "user", "content": content}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")

async def json_call(prompt: str, *, model: str = CHEAP, max_tokens: int = 512) -> dict:
    raw = await text(prompt + "\n\nRespond with a single valid JSON object, no prose.",
                     model=model, max_tokens=max_tokens)
    # Tolerate surrounding text by extracting first {...} block.
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON in response: {raw!r}")
    return json.loads(raw[start:end + 1])
```

- [ ] **Step 4: Implement tools**

`packages/reference-agent/src/arxiv_agent/tools.py`:

```python
from __future__ import annotations
from dataclasses import dataclass
from .mock_arxiv.client import get_arxiv_client
from .mock_arxiv.mock import PaperSummary, Paper
from . import llm

@dataclass(frozen=True)
class CandidateScore:
    paper_id: str
    score: float
    rationale: str

@dataclass(frozen=True)
class FigureDescription:
    paper_id: str
    caption: str
    description: str

@dataclass(frozen=True)
class Summary:
    paper_id: str
    text: str

# Internal indirection so tests can monkeypatch.
async def _llm_json(prompt: str) -> str:
    raw = await llm.text(prompt + "\n\nRespond with a single valid JSON object, no prose.")
    start, end = raw.find("{"), raw.rfind("}")
    return raw[start:end + 1] if start != -1 and end != -1 else raw

async def search_arxiv(query: str, limit: int = 10,
                       date_from: str | None = None, date_to: str | None = None) -> list[PaperSummary]:
    return get_arxiv_client().search(query, limit=limit, date_from=date_from, date_to=date_to)

async def fetch_metadata(paper_id: str) -> PaperSummary:
    return get_arxiv_client().fetch_metadata(paper_id)

async def fetch_paper(paper_id: str) -> Paper:
    return get_arxiv_client().fetch_paper(paper_id)

async def score_candidate(metadata_id: str, research_interest: str) -> CandidateScore:
    meta = get_arxiv_client().fetch_metadata(metadata_id)
    prompt = (
        f"Research interest: {research_interest}\n\n"
        f"Paper title: {meta.title}\n"
        f"Abstract: {meta.abstract}\n\n"
        "How relevant is this paper to the research interest? "
        "Return JSON with fields: score (float 0..1), rationale (one short sentence)."
    )
    import json as _json
    data = _json.loads(await _llm_json(prompt))
    return CandidateScore(paper_id=metadata_id,
                          score=float(data["score"]),
                          rationale=str(data["rationale"]))

async def extract_figures(paper_id: str) -> list[FigureDescription]:
    figs = get_arxiv_client().extract_figures(paper_id)
    out: list[FigureDescription] = []
    for f in figs:
        desc = await llm.vision(
            "Describe what this figure shows in 1–2 sentences. Be specific.",
            f.data, content_type=f.content_type,
        )
        out.append(FigureDescription(paper_id=paper_id, caption=f.caption, description=desc))
    return out

async def summarize(paper_id: str, focus: str) -> Summary:
    paper = get_arxiv_client().fetch_paper(paper_id)
    prompt = (
        f"Summarize the following paper with focus on '{focus}'. "
        "3-5 bullets, terse, technical voice.\n\n"
        f"Title: {paper.title}\n\n{paper.body[:6000]}"
    )
    summary = await llm.text(prompt, max_tokens=600)
    return Summary(paper_id=paper_id, text=summary)

async def query_paper(paper_id: str, question: str) -> str:
    paper = get_arxiv_client().fetch_paper(paper_id)
    prompt = (
        f"Paper: {paper.title}\n\n{paper.body[:8000]}\n\n"
        f"Question: {question}\n\nAnswer concisely, citing specific text where useful."
    )
    return await llm.text(prompt, max_tokens=600, model=llm.QUALITY)

async def compose_digest(papers: list[Summary], research_interest: str) -> str:
    bullets = "\n\n".join(f"### {s.paper_id}\n{s.text}" for s in papers)
    prompt = (
        f"You are producing a weekly research digest for: {research_interest}\n\n"
        "Compose a Markdown digest with:\n"
        "1. A 2-sentence overview tying the papers together.\n"
        "2. Per-paper sections (already drafted below) — keep them.\n"
        "3. A 'What this means for practitioners' closing of 2–3 bullets.\n\n"
        f"Drafted summaries:\n\n{bullets}"
    )
    return await llm.text(prompt, max_tokens=2000, model=llm.QUALITY)
```

- [ ] **Step 5: Run tests, fix any issues, expect PASS**

```bash
uv run pytest packages/reference-agent/tests/test_tools.py -v
```

The vision test (`test_extract_figures_returns_descriptions`) will make a real Anthropic call. If you don't want that in unit tests, mark it `@pytest.mark.live` and skip by default; only the `score_candidate` test should be required for green. Adjust as needed.

- [ ] **Step 6: Commit and close**

```bash
git add packages/reference-agent
git commit -m "implement 8 reference-agent tools over mock arxiv"
bd close <id>
```

---

### Task 4: Worker agent (Pydantic AI)

**Goal:** Pydantic AI agent for the worker role: takes a paper_id + research interest, calls `fetch_paper`, `extract_figures`, `summarize`, returns a `WorkerResult`. Multi-modal capable.

**Files:**
- Create: `packages/reference-agent/src/arxiv_agent/worker.py`
- Create: `packages/reference-agent/src/arxiv_agent/prompts/worker.md`
- Test: `packages/reference-agent/tests/test_worker.py`

- [ ] **Step 1: bd issue and claim**

```bash
bd create --title="Task 4: worker agent in pydantic ai" --type=task --priority=2 \
  --description="Worker agent: deep-read a paper using fetch_paper/extract_figures/summarize/query_paper"
bd update <id> --claim
```

- [ ] **Step 2: Author worker prompt**

`packages/reference-agent/src/arxiv_agent/prompts/worker.md`:

```markdown
You are the Worker agent in AgentAid's arXiv research pipeline.

Your job: given a paper_id and a research_interest, deep-read the paper and produce a structured summary that the Planner will weave into a digest.

Always:
1. Call `fetch_paper(paper_id)` first to load the body.
2. Call `extract_figures(paper_id)` to get figure descriptions (multi-modal).
3. Call `summarize(paper_id, focus=<research_interest>)` to produce the bullet-form summary.
4. Optionally call `query_paper(paper_id, question)` only if the user asked a follow-up question.

Return a `WorkerResult` with the paper_id, the summary text, the figure descriptions, and any answer to the follow-up question.

Do not call other tools. Do not call tools you have already called once unless the user explicitly asked for a re-read.
```

- [ ] **Step 3: Write failing test**

`packages/reference-agent/tests/test_worker.py`:

```python
import pytest
from arxiv_agent.worker import build_worker_agent, WorkerInput, WorkerResult

@pytest.mark.asyncio
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
    with pytest.raises(Exception):
        WorkerInput(paper_id="", research_interest="x")
```

Run: `uv run pytest packages/reference-agent/tests/test_worker.py::test_worker_input_model_validates -v`
Expected: FAIL (worker module missing).

- [ ] **Step 4: Implement worker agent**

`packages/reference-agent/src/arxiv_agent/worker.py`:

```python
from __future__ import annotations
from importlib.resources import files
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from . import tools

class WorkerInput(BaseModel):
    paper_id: str = Field(min_length=1)
    research_interest: str = Field(min_length=1)
    follow_up_question: str | None = None

class FigureDescription(BaseModel):
    caption: str
    description: str

class WorkerResult(BaseModel):
    paper_id: str
    summary: str
    figure_descriptions: list[FigureDescription]
    follow_up_answer: str | None = None

def _prompt() -> str:
    return (files("arxiv_agent.prompts") / "worker.md").read_text(encoding="utf-8")

def build_worker_agent() -> Agent[WorkerInput, WorkerResult]:
    model = AnthropicModel("claude-sonnet-4-6")
    agent: Agent[WorkerInput, WorkerResult] = Agent(
        model=model,
        deps_type=WorkerInput,
        result_type=WorkerResult,
        system_prompt=_prompt(),
    )

    @agent.tool
    async def fetch_paper(ctx: RunContext[WorkerInput], paper_id: str) -> str:
        p = await tools.fetch_paper(paper_id)
        return p.body

    @agent.tool
    async def extract_figures(ctx: RunContext[WorkerInput], paper_id: str) -> list[dict]:
        descs = await tools.extract_figures(paper_id)
        return [{"caption": d.caption, "description": d.description} for d in descs]

    @agent.tool
    async def summarize(ctx: RunContext[WorkerInput], paper_id: str, focus: str) -> str:
        s = await tools.summarize(paper_id, focus)
        return s.text

    @agent.tool
    async def query_paper(ctx: RunContext[WorkerInput], paper_id: str, question: str) -> str:
        return await tools.query_paper(paper_id, question)

    return agent
```

- [ ] **Step 5: Run validation test, expect PASS**

```bash
uv run pytest packages/reference-agent/tests/test_worker.py::test_worker_input_model_validates -v
```

Expected: PASS.

- [ ] **Step 6: Run live test (manual gate)**

The live test calls Anthropic. Run only when ready to spend tokens:

```bash
uv run pytest packages/reference-agent/tests/test_worker.py -m live -v
```

Expected: PASS, with a non-empty summary and at least one figure description for paper `2401.00001`.

- [ ] **Step 7: Commit and close**

```bash
git add packages/reference-agent
git commit -m "implement worker agent in pydantic ai"
bd close <id>
```

---

### Task 5: Planner agent + end-to-end run + golden dataset

**Goal:** Planner agent that orchestrates: searches, scores candidates, spawns workers (one per top-N candidate), composes the digest. Plus the 10-row golden dataset under `eval/golden/dataset.json`. Plus a CLI entry point so `make agent` runs an end-to-end demo.

**Files:**
- Create: `packages/reference-agent/src/arxiv_agent/planner.py`
- Create: `packages/reference-agent/src/arxiv_agent/prompts/planner.md`
- Create: `packages/reference-agent/src/arxiv_agent/__main__.py`
- Create: `eval/golden/dataset.json`
- Test: `packages/reference-agent/tests/test_planner.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 5: planner agent + golden dataset + e2e demo" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Author planner prompt**

`packages/reference-agent/src/arxiv_agent/prompts/planner.md`:

```markdown
You are the Planner agent for AgentAid's arXiv research pipeline.

Inputs: a research_interest string and a date_window (from, to).

Your job, in order:
1. Call `search_arxiv(query, limit, date_from, date_to)` to find candidate papers.
2. For each candidate (up to 6), call `fetch_metadata(paper_id)` and `score_candidate(metadata_id, research_interest)`.
3. Pick the top 3 by score. For each, call `dispatch_worker(paper_id, research_interest)` to get a deep summary.
4. Call `compose_digest(papers, research_interest)` to produce the final Markdown digest.
5. Return a `PlannerResult` with the digest and the per-paper scores.

Be efficient — never call the same tool twice with the same arguments. Keep total worker dispatches ≤ 4.
```

- [ ] **Step 3: Write tests**

`packages/reference-agent/tests/test_planner.py`:

```python
import pytest
from arxiv_agent.planner import build_planner_agent, PlannerInput, PlannerResult

def test_planner_input_validates() -> None:
    PlannerInput(research_interest="concept drift", date_from="2024-01-01", date_to="2024-12-31")
    with pytest.raises(Exception):
        PlannerInput(research_interest="", date_from="2024-01-01", date_to="2024-12-31")

@pytest.mark.asyncio
@pytest.mark.live
async def test_planner_produces_digest_for_drift_interest() -> None:
    agent = build_planner_agent()
    res = await agent.run(PlannerInput(
        research_interest="concept drift detection in streaming ML",
        date_from="2024-01-01", date_to="2024-12-31",
    ))
    assert isinstance(res.output, PlannerResult)
    assert "##" in res.output.digest          # has Markdown sections
    assert len(res.output.candidates) >= 3
    assert res.output.candidates[0].score >= 0.0
```

Run the validation-only test: `uv run pytest packages/reference-agent/tests/test_planner.py::test_planner_input_validates -v`
Expected: FAIL (planner module missing).

- [ ] **Step 4: Implement planner**

`packages/reference-agent/src/arxiv_agent/planner.py`:

```python
from __future__ import annotations
from importlib.resources import files
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from . import tools
from .worker import build_worker_agent, WorkerInput

class PlannerInput(BaseModel):
    research_interest: str = Field(min_length=1)
    date_from: str
    date_to: str

class CandidateRecord(BaseModel):
    paper_id: str
    title: str
    score: float
    rationale: str

class PaperSection(BaseModel):
    paper_id: str
    summary: str

class PlannerResult(BaseModel):
    digest: str
    candidates: list[CandidateRecord]
    sections: list[PaperSection]

def _prompt() -> str:
    return (files("arxiv_agent.prompts") / "planner.md").read_text(encoding="utf-8")

def build_planner_agent() -> Agent[PlannerInput, PlannerResult]:
    worker = build_worker_agent()
    model = AnthropicModel("claude-sonnet-4-6")
    agent: Agent[PlannerInput, PlannerResult] = Agent(
        model=model,
        deps_type=PlannerInput,
        result_type=PlannerResult,
        system_prompt=_prompt(),
    )

    @agent.tool
    async def search_arxiv(ctx: RunContext[PlannerInput], query: str, limit: int = 6) -> list[dict]:
        results = await tools.search_arxiv(query, limit=limit,
                                           date_from=ctx.deps.date_from,
                                           date_to=ctx.deps.date_to)
        return [{"id": r.id, "title": r.title, "abstract": r.abstract,
                 "published": r.published} for r in results]

    @agent.tool
    async def fetch_metadata(ctx: RunContext[PlannerInput], paper_id: str) -> dict:
        m = await tools.fetch_metadata(paper_id)
        return {"id": m.id, "title": m.title, "abstract": m.abstract,
                "authors": list(m.authors), "published": m.published}

    @agent.tool
    async def score_candidate(ctx: RunContext[PlannerInput],
                              metadata_id: str) -> dict:
        s = await tools.score_candidate(metadata_id, ctx.deps.research_interest)
        return {"paper_id": s.paper_id, "score": s.score, "rationale": s.rationale}

    @agent.tool
    async def dispatch_worker(ctx: RunContext[PlannerInput], paper_id: str) -> dict:
        res = await worker.run(WorkerInput(
            paper_id=paper_id,
            research_interest=ctx.deps.research_interest,
        ))
        return {"paper_id": res.output.paper_id, "summary": res.output.summary}

    @agent.tool
    async def compose_digest(ctx: RunContext[PlannerInput],
                             sections: list[dict]) -> str:
        from .tools import Summary
        summaries = [Summary(paper_id=s["paper_id"], text=s["summary"]) for s in sections]
        return await tools.compose_digest(summaries, ctx.deps.research_interest)

    return agent
```

- [ ] **Step 5: CLI entry**

`packages/reference-agent/src/arxiv_agent/__main__.py`:

```python
from __future__ import annotations
import asyncio
import json
import sys
from .planner import build_planner_agent, PlannerInput

async def _main(research_interest: str, date_from: str, date_to: str) -> None:
    agent = build_planner_agent()
    res = await agent.run(PlannerInput(
        research_interest=research_interest,
        date_from=date_from, date_to=date_to,
    ))
    print(json.dumps({
        "digest": res.output.digest,
        "candidates": [c.model_dump() for c in res.output.candidates],
    }, indent=2))

if __name__ == "__main__":
    interest = sys.argv[1] if len(sys.argv) > 1 else "concept drift detection in streaming ML"
    df = sys.argv[2] if len(sys.argv) > 2 else "2024-01-01"
    dt = sys.argv[3] if len(sys.argv) > 3 else "2024-12-31"
    asyncio.run(_main(interest, df, dt))
```

- [ ] **Step 6: Author golden dataset**

`eval/golden/dataset.json`:

```json
{
  "name": "arxiv-research-digest-v1",
  "description": "Golden inputs for the arXiv research digest agent. 10 (research_interest, date_window) → expected paper ids and themes.",
  "rows": [
    {
      "id": "row-001",
      "input": {
        "research_interest": "concept drift detection in streaming ML",
        "date_from": "2024-01-01",
        "date_to": "2024-06-30"
      },
      "expected": {
        "expected_paper_ids": ["2401.00001"],
        "expected_themes": ["adaptive windowing", "Hoeffding bound"]
      }
    },
    {
      "id": "row-002",
      "input": {
        "research_interest": "Page-Hinkley applied to LLM evaluation streams",
        "date_from": "2024-01-01",
        "date_to": "2024-12-31"
      },
      "expected": {
        "expected_paper_ids": ["2402.00012"],
        "expected_themes": ["change-point detection", "evaluation stream"]
      }
    }
  ]
}
```

(Author 8 more `rows` matching themes available in the seed corpus from Task 2.)

- [ ] **Step 7: Run validation test, expect PASS**

```bash
uv run pytest packages/reference-agent/tests/test_planner.py::test_planner_input_validates -v
```

- [ ] **Step 8: Manual end-to-end smoke**

```bash
uv run python -m arxiv_agent
```

Expected: prints JSON with a Markdown `digest` field containing at least one `##` section per top paper, and a `candidates` array of length ≥ 3.

- [ ] **Step 9: Commit and close**

```bash
git add packages/reference-agent eval/golden
git commit -m "implement planner agent and 10-row golden dataset"
bd close <id>
```

---

## Phase 2 — Python SDK Instrumentation (Day 2, ~5h)

### Task 6: agentaid-py package + Pydantic data models

**Goal:** Set up the `agentaid` package skeleton and the shared Pydantic models that flow across SDK ↔ server (Run, Span, EvalResult, Golden, DriftState). These are the typed data shapes the rest of the system uses.

**Files:**
- Create: `packages/agentaid-py/src/agentaid/__init__.py`
- Create: `packages/agentaid-py/src/agentaid/models.py`
- Test: `packages/agentaid-py/tests/test_models.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 6: agentaid-py package + shared models" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Failing test**

`packages/agentaid-py/tests/test_models.py`:

```python
import pytest
from datetime import datetime
from agentaid.models import Run, Span, EvalResult, EvalMode, DriftState, DriftSignal

def test_run_round_trips() -> None:
    r = Run(id="run-1", agent_name="arxiv", started_at=datetime.utcnow(),
            input={"x": 1}, output=None, prompt_sha="abcd", model="claude-haiku-4-5",
            total_cost=0.01, total_tokens=420, status="running")
    assert Run.model_validate_json(r.model_dump_json()) == r

def test_eval_result_unit_interval_score() -> None:
    EvalResult(run_id="r", eval_name="x", mode=EvalMode.ONLINE, score=0.5)
    with pytest.raises(Exception):
        EvalResult(run_id="r", eval_name="x", mode=EvalMode.ONLINE, score=1.5)

def test_drift_state_signals_enum_complete() -> None:
    assert {s.value for s in DriftSignal} == {"input", "tool_call", "quality"}
```

Run: `uv run pytest packages/agentaid-py/tests/test_models.py -v` → FAIL.

- [ ] **Step 3: Implement models**

`packages/agentaid-py/src/agentaid/models.py`:

```python
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict

class EvalMode(str, Enum):
    ONLINE = "online"
    REGRESSION = "regression"
    INVARIANT = "invariant"

class DriftSignal(str, Enum):
    INPUT = "input"
    TOOL_CALL = "tool_call"
    QUALITY = "quality"

RunStatus = Literal["running", "succeeded", "failed"]

class Span(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    run_id: str
    parent_span_id: str | None = None
    name: str
    role: str | None = None         # "planner" | "worker" | "tool" | etc.
    started_at: datetime
    ended_at: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)

class Run(BaseModel):
    id: str
    agent_name: str
    started_at: datetime
    ended_at: datetime | None = None
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    prompt_sha: str | None = None
    model: str | None = None
    total_cost: float = 0.0
    total_tokens: int = 0
    status: RunStatus = "running"

class EvalResult(BaseModel):
    run_id: str
    eval_name: str
    mode: EvalMode
    score: float = Field(ge=0.0, le=1.0)
    label: str | None = None
    rationale: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Golden(BaseModel):
    id: str
    input: dict[str, Any]
    expected: dict[str, Any]

class DriftState(BaseModel):
    signal: DriftSignal
    detector_name: str
    window: str             # e.g. "100" or "7d"
    value: float
    threshold: float
    is_drifted: bool
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

`packages/agentaid-py/src/agentaid/__init__.py`:

```python
from .models import (
    Run, Span, EvalResult, EvalMode, Golden, DriftState, DriftSignal, RunStatus,
)

__all__ = [
    "Run", "Span", "EvalResult", "EvalMode", "Golden",
    "DriftState", "DriftSignal", "RunStatus",
]
```

- [ ] **Step 4: Run tests, expect PASS**

```bash
uv run pytest packages/agentaid-py/tests/test_models.py -v
```

- [ ] **Step 5: Commit and close**

```bash
git add packages/agentaid-py
git commit -m "add agentaid shared pydantic models"
bd close <id>
```

---

### Task 7: OTel/GenAI exporter

**Goal:** A small OTel exporter that translates OpenTelemetry spans into the AgentAid wire format (JSON over HTTP POST) using GenAI semantic conventions. The reference agent installs this exporter to ship spans to the AgentAid server.

**Files:**
- Create: `packages/agentaid-py/src/agentaid/otel/__init__.py`
- Create: `packages/agentaid-py/src/agentaid/otel/conventions.py`
- Create: `packages/agentaid-py/src/agentaid/otel/exporter.py`
- Create: `packages/agentaid-py/src/agentaid/otel/setup.py`
- Test: `packages/agentaid-py/tests/test_otel_exporter.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 7: otel/genai exporter for agentaid-py" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Failing test**

`packages/agentaid-py/tests/test_otel_exporter.py`:

```python
import json
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from agentaid.otel.exporter import AgentAidSpanExporter, _serialize_span
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanContext, TraceFlags
from opentelemetry.trace.span import format_span_id, format_trace_id

def _make_readable_span() -> ReadableSpan:
    ctx = SpanContext(trace_id=0x12345678901234567890123456789012,
                      span_id=0xabcdef0123456789, is_remote=False,
                      trace_flags=TraceFlags(0x01))
    return ReadableSpan(
        name="planner.dispatch_worker",
        context=ctx,
        parent=None,
        attributes={"gen_ai.system": "anthropic", "gen_ai.request.model": "claude-haiku-4-5",
                    "agentaid.role": "planner", "agentaid.run_id": "run-001"},
        start_time=int(datetime(2026, 5, 6, 12, 0, 0).timestamp() * 1e9),
        end_time=int(datetime(2026, 5, 6, 12, 0, 1).timestamp() * 1e9),
    )

def test_serialize_span_emits_genai_attributes() -> None:
    span = _make_readable_span()
    payload = _serialize_span(span)
    assert payload["name"] == "planner.dispatch_worker"
    assert payload["attributes"]["gen_ai.system"] == "anthropic"
    assert payload["attributes"]["agentaid.role"] == "planner"
    assert payload["span_id"] == format_span_id(0xabcdef0123456789)
    assert payload["trace_id"] == format_trace_id(0x12345678901234567890123456789012)

@pytest.mark.asyncio
async def test_exporter_posts_to_endpoint() -> None:
    span = _make_readable_span()
    exporter = AgentAidSpanExporter(endpoint="http://localhost:8000/ingest")
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=type("R", (), {"status_code": 200})())) as p:
        result = exporter.export([span])
        # SimpleSpanProcessor calls export synchronously; we wrap async internally.
        await exporter._flush()
    assert result.name == "SUCCESS"
    p.assert_called()
    body = p.call_args.kwargs["json"]
    assert "spans" in body
    assert body["spans"][0]["attributes"]["gen_ai.system"] == "anthropic"
```

Run: `uv run pytest packages/agentaid-py/tests/test_otel_exporter.py -v` → FAIL.

- [ ] **Step 3: Implement conventions helpers**

`packages/agentaid-py/src/agentaid/otel/conventions.py`:

```python
from __future__ import annotations
from enum import StrEnum

class GenAI(StrEnum):
    SYSTEM = "gen_ai.system"
    REQUEST_MODEL = "gen_ai.request.model"
    RESPONSE_MODEL = "gen_ai.response.model"
    USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
    USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
    OPERATION_NAME = "gen_ai.operation.name"   # "chat" | "embeddings" | "agent.run" | etc.
    TOOL_NAME = "gen_ai.tool.name"
    TOOL_CALL_ID = "gen_ai.tool.call.id"

class AgentAid(StrEnum):
    """AgentAid-specific extensions (namespaced; complementary to gen_ai.*)."""
    RUN_ID = "agentaid.run_id"
    ROLE = "agentaid.role"                      # "planner" | "worker" | "tool"
    PROMPT_SHA = "agentaid.prompt_sha"
    AGENT_NAME = "agentaid.agent_name"
    EVAL_RESULT = "agentaid.eval_result"        # JSON string for invariant evals
    INPUT = "agentaid.input"                    # serialized run input
    OUTPUT = "agentaid.output"                  # serialized run output
```

- [ ] **Step 4: Implement exporter**

`packages/agentaid-py/src/agentaid/otel/exporter.py`:

```python
from __future__ import annotations
import asyncio
import json
import logging
from typing import Sequence
import httpx
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace.span import format_span_id, format_trace_id

log = logging.getLogger(__name__)

def _serialize_span(span: ReadableSpan) -> dict:
    ctx = span.get_span_context()
    parent = span.parent
    return {
        "trace_id": format_trace_id(ctx.trace_id),
        "span_id": format_span_id(ctx.span_id),
        "parent_span_id": format_span_id(parent.span_id) if parent else None,
        "name": span.name,
        "kind": str(span.kind),
        "start_time_unix_nano": span.start_time,
        "end_time_unix_nano": span.end_time,
        "attributes": dict(span.attributes or {}),
        "events": [
            {"name": e.name, "timestamp_unix_nano": e.timestamp,
             "attributes": dict(e.attributes or {})}
            for e in (span.events or [])
        ],
        "status": {"code": span.status.status_code.name,
                   "description": span.status.description or ""},
    }

class AgentAidSpanExporter(SpanExporter):
    """OTel exporter that POSTs serialized spans to the AgentAid server."""
    def __init__(self, endpoint: str = "http://localhost:8000/ingest", timeout: float = 5.0) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._pending: list[asyncio.Task] = []

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        payload = {"spans": [_serialize_span(s) for s in spans]}
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        if loop.is_running():
            self._pending.append(loop.create_task(self._post(payload)))
        else:
            loop.run_until_complete(self._post(payload))
        return SpanExportResult.SUCCESS

    async def _post(self, payload: dict) -> None:
        try:
            await self._client.post(self.endpoint, json=payload)
        except Exception:
            log.warning("agentaid exporter failed", exc_info=True)

    async def _flush(self) -> None:
        if self._pending:
            await asyncio.gather(*self._pending, return_exceptions=True)
            self._pending.clear()

    def shutdown(self) -> None:
        try:
            asyncio.get_event_loop().run_until_complete(self._client.aclose())
        except Exception:
            pass
```

- [ ] **Step 5: Setup helper**

`packages/agentaid-py/src/agentaid/otel/setup.py`:

```python
from __future__ import annotations
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from .exporter import AgentAidSpanExporter

def install(endpoint: str | None = None, *, service_name: str = "agentaid-agent") -> None:
    """Wire the AgentAid exporter into OTel's global tracer provider."""
    provider = TracerProvider()
    exporter = AgentAidSpanExporter(endpoint or os.getenv("AGENTAID_ENDPOINT", "http://localhost:8000/ingest"))
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
```

`packages/agentaid-py/src/agentaid/otel/__init__.py`:

```python
from .conventions import GenAI, AgentAid
from .exporter import AgentAidSpanExporter
from .setup import install

__all__ = ["GenAI", "AgentAid", "AgentAidSpanExporter", "install"]
```

- [ ] **Step 6: Run tests, expect PASS**

```bash
uv run pytest packages/agentaid-py/tests/test_otel_exporter.py -v
```

- [ ] **Step 7: Commit and close**

```bash
git add packages/agentaid-py
git commit -m "add otel/genai span exporter for agentaid"
bd close <id>
```

---

### Task 8: Wire reference agent → SDK; verify spans emit

**Goal:** Configure the reference agent to emit spans through the AgentAid exporter. End the task with a captured payload showing real spans flowing.

**Files:**
- Modify: `packages/reference-agent/src/arxiv_agent/__main__.py` (call `agentaid.otel.install()` at startup)
- Modify: `packages/reference-agent/src/arxiv_agent/planner.py` (annotate runs with `AgentAid.*` attributes)
- Modify: `packages/reference-agent/src/arxiv_agent/worker.py` (same)
- Test: `packages/reference-agent/tests/test_otel_emission.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 8: wire reference agent to agentaid otel exporter" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Failing test**

`packages/reference-agent/tests/test_otel_emission.py`:

```python
import json
import pytest
from typing import Any
from unittest.mock import patch
from opentelemetry.sdk.trace import ReadableSpan
from arxiv_agent import planner

class _CaptureExporter:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, Any]]] = []

    def export(self, spans):
        from agentaid.otel.exporter import _serialize_span
        self.calls.append([_serialize_span(s) for s in spans])
        from opentelemetry.sdk.trace.export import SpanExportResult
        return SpanExportResult.SUCCESS

    def shutdown(self): pass

@pytest.mark.asyncio
@pytest.mark.live
async def test_planner_emits_agentaid_attributes(monkeypatch) -> None:
    cap = _CaptureExporter()
    monkeypatch.setattr("agentaid.otel.setup.AgentAidSpanExporter", lambda *a, **k: cap)
    import agentaid.otel as otel
    otel.install()
    agent = planner.build_planner_agent()
    await agent.run(planner.PlannerInput(
        research_interest="concept drift",
        date_from="2024-01-01", date_to="2024-12-31",
    ))
    flat = [s for batch in cap.calls for s in batch]
    assert any(s["attributes"].get("agentaid.role") == "planner" for s in flat)
```

(Validation-only assertions go in a separate non-live test if you want a fast green; the meaningful check requires a real run.)

- [ ] **Step 3: Annotate roles in planner / worker**

In `worker.py`, before `return agent` add:

```python
    @agent.system_prompt
    def _augment(ctx: RunContext[WorkerInput]) -> str:
        # Mark the current span with role info — Pydantic AI propagates via context.
        from opentelemetry import trace
        span = trace.get_current_span()
        span.set_attribute("agentaid.role", "worker")
        span.set_attribute("agentaid.agent_name", "arxiv-worker")
        return ""
```

Equivalent in `planner.py` with `agentaid.role = "planner"` and `agentaid.agent_name = "arxiv-planner"`. (If Pydantic AI's hook surface differs at the version pinned in Task 1, fall back to a manual `tracer.start_as_current_span` wrapper around `agent.run` — keep the attribute names and roles the same.)

- [ ] **Step 4: Install in `__main__`**

Modify `packages/reference-agent/src/arxiv_agent/__main__.py`:

Replace the existing imports/main with:

```python
from __future__ import annotations
import asyncio
import json
import sys
from agentaid.otel import install as install_otel
from .planner import build_planner_agent, PlannerInput

async def _main(research_interest: str, date_from: str, date_to: str) -> None:
    install_otel()
    agent = build_planner_agent()
    res = await agent.run(PlannerInput(
        research_interest=research_interest,
        date_from=date_from, date_to=date_to,
    ))
    print(json.dumps({
        "digest": res.output.digest,
        "candidates": [c.model_dump() for c in res.output.candidates],
    }, indent=2))

if __name__ == "__main__":
    interest = sys.argv[1] if len(sys.argv) > 1 else "concept drift detection in streaming ML"
    df = sys.argv[2] if len(sys.argv) > 2 else "2024-01-01"
    dt = sys.argv[3] if len(sys.argv) > 3 else "2024-12-31"
    asyncio.run(_main(interest, df, dt))
```

- [ ] **Step 5: Smoke run with capture**

Run a tiny inline harness to print spans without needing the server (sanity check before Task 11):

```bash
uv run python -c "
import asyncio, json
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from arxiv_agent.planner import build_planner_agent, PlannerInput

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

async def main():
    agent = build_planner_agent()
    await agent.run(PlannerInput(research_interest='concept drift', date_from='2024-01-01', date_to='2024-12-31'))

asyncio.run(main())
" | head -200
```

Expected: a stream of JSON spans printed to stdout, including spans with `agentaid.role` attributes for planner and worker invocations and `gen_ai.*` attributes for model calls.

- [ ] **Step 6: Commit and close**

```bash
git add packages/reference-agent packages/agentaid-py
git commit -m "wire reference agent to agentaid otel exporter"
bd close <id>
```

---

## Phase 3 — Server Foundation (Day 3, ~12h)

### Task 9: FastAPI server scaffold + SQLModel schema

**Goal:** A runnable FastAPI app with SQLModel-backed SQLite, defining `Run`, `Span`, `EvalResult`, `DriftStateRow`, `Dataset`, `DatasetRow`, `RegressionRun` tables and a healthcheck endpoint.

**Files:**
- Create: `packages/agentaid-server/src/agentaid_server/__init__.py`
- Create: `packages/agentaid-server/src/agentaid_server/config.py`
- Create: `packages/agentaid-server/src/agentaid_server/db/__init__.py`
- Create: `packages/agentaid-server/src/agentaid_server/db/engine.py`
- Create: `packages/agentaid-server/src/agentaid_server/db/models.py`
- Create: `packages/agentaid-server/src/agentaid_server/main.py`
- Test: `packages/agentaid-server/tests/test_app_boot.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 9: fastapi scaffold + sqlmodel schema" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Failing test**

`packages/agentaid-server/tests/test_app_boot.py`:

```python
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
    # Re-import to pick up env
    import importlib, agentaid_server.db.engine as eng
    importlib.reload(eng)
    from agentaid_server.db.engine import engine, init_db
    await init_db()
    import sqlite3
    conn = sqlite3.connect(db_path)
    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"run", "span", "evalresult", "driftstaterow", "dataset",
            "datasetrow", "regressionrun"} <= names
```

Run: `uv run pytest packages/agentaid-server/tests/test_app_boot.py -v` → FAIL.

- [ ] **Step 3: Config**

`packages/agentaid-server/src/agentaid_server/config.py`:

```python
from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENTAID_", env_file=".env", extra="ignore")
    db_url: str = "sqlite+aiosqlite:///./agentaid.db"
    online_eval_sample_rate: float = 1.0
    judge_model_default: str = "claude-haiku-4-5"
    cost_budget_default: float = 0.50

settings = Settings()
```

- [ ] **Step 4: Engine**

`packages/agentaid-server/src/agentaid_server/db/engine.py`:

```python
from __future__ import annotations
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlmodel import SQLModel
from ..config import settings

engine = create_async_engine(settings.db_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db() -> None:
    # Import models so SQLModel.metadata is populated.
    from . import models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def session() -> AsyncSession:
    async with SessionLocal() as s:
        yield s
```

- [ ] **Step 5: Models**

`packages/agentaid-server/src/agentaid_server/db/models.py`:

```python
from __future__ import annotations
from datetime import datetime
from typing import Any
from sqlmodel import SQLModel, Field, JSON, Column

class Run(SQLModel, table=True):
    id: str = Field(primary_key=True)
    agent_name: str
    started_at: datetime
    ended_at: datetime | None = None
    status: str = "running"
    prompt_sha: str | None = None
    model: str | None = None
    total_cost: float = 0.0
    total_tokens: int = 0
    input: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    output: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

class Span(SQLModel, table=True):
    id: str = Field(primary_key=True)
    run_id: str = Field(index=True, foreign_key="run.id")
    parent_span_id: str | None = Field(default=None, index=True)
    name: str
    role: str | None = Field(default=None, index=True)
    started_at: datetime
    ended_at: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    events: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))

class EvalResult(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(index=True, foreign_key="run.id")
    eval_name: str = Field(index=True)
    mode: str
    score: float
    label: str | None = None
    rationale: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DriftStateRow(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    signal: str = Field(index=True)
    detector_name: str
    window: str
    value: float
    threshold: float
    is_drifted: bool
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Dataset(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    description: str | None = None

class DatasetRow(SQLModel, table=True):
    id: str = Field(primary_key=True)
    dataset_id: str = Field(index=True, foreign_key="dataset.id")
    input: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    expected: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

class RegressionRun(SQLModel, table=True):
    id: str = Field(primary_key=True)
    dataset_id: str = Field(index=True, foreign_key="dataset.id")
    prompt_sha: str | None = None
    model: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    status: str = "running"
    summary: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
```

- [ ] **Step 6: App entry**

`packages/agentaid-server/src/agentaid_server/main.py`:

```python
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db.engine import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="AgentAid", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 7: Run tests, expect PASS**

```bash
uv run pytest packages/agentaid-server/tests/test_app_boot.py -v
```

- [ ] **Step 8: Manual smoke**

```bash
uv run uvicorn agentaid_server.main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/healthz
kill %1
```

Expected: `{"status":"ok"}`.

- [ ] **Step 9: Commit and close**

```bash
git add packages/agentaid-server
git commit -m "scaffold agentaid-server with sqlmodel schema"
bd close <id>
```

---

### Task 10: OTel/GenAI ingestion endpoint

**Goal:** `POST /ingest` accepts the AgentAid wire format from Task 7, parses spans, upserts the run record, writes spans, evaluates Mode 3 invariants inline (deferred to Task 17 for actual eval execution; this task only persists). Returns 202.

**Files:**
- Create: `packages/agentaid-server/src/agentaid_server/api/__init__.py`
- Create: `packages/agentaid-server/src/agentaid_server/api/ingest.py`
- Create: `packages/agentaid-server/src/agentaid_server/ingestion/__init__.py`
- Create: `packages/agentaid-server/src/agentaid_server/ingestion/parser.py`
- Modify: `packages/agentaid-server/src/agentaid_server/main.py` (mount router)
- Test: `packages/agentaid-server/tests/test_ingest.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 10: otel ingestion endpoint" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Failing test**

`packages/agentaid-server/tests/test_ingest.py`:

```python
import pytest
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from sqlmodel import select
from agentaid_server.main import app
from agentaid_server.db.engine import SessionLocal
from agentaid_server.db.models import Run, Span

def _ns(dt: datetime) -> int:
    return int(dt.timestamp() * 1e9)

@pytest.mark.asyncio
async def test_ingest_creates_run_and_spans(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTAID_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'t.db'}")
    import importlib, agentaid_server.db.engine as eng, agentaid_server.main as mn
    importlib.reload(eng); importlib.reload(mn)
    from agentaid_server.main import app as fresh_app

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
```

Run: `uv run pytest packages/agentaid-server/tests/test_ingest.py -v` → FAIL.

- [ ] **Step 3: Implement parser**

`packages/agentaid-server/src/agentaid_server/ingestion/parser.py`:

```python
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any
from agentaid.otel.conventions import GenAI, AgentAid
from ..db.models import Run, Span as DbSpan

def _ts_from_nano(nano: int | None) -> datetime | None:
    if nano is None:
        return None
    return datetime.fromtimestamp(nano / 1e9, tz=timezone.utc).replace(tzinfo=None)

def parse_span(raw: dict) -> DbSpan:
    attrs = dict(raw.get("attributes", {}))
    return DbSpan(
        id=raw["span_id"],
        run_id=str(attrs.get(AgentAid.RUN_ID, "")),
        parent_span_id=raw.get("parent_span_id"),
        name=raw["name"],
        role=attrs.get(AgentAid.ROLE),
        started_at=_ts_from_nano(raw["start_time_unix_nano"]) or datetime.utcnow(),
        ended_at=_ts_from_nano(raw.get("end_time_unix_nano")),
        attributes=attrs,
        events=list(raw.get("events", [])),
    )

def derive_run(spans: list[DbSpan]) -> Run | None:
    """Reconstruct a Run from the root-most span carrying agentaid.run_id."""
    candidates = [s for s in spans if s.run_id]
    if not candidates:
        return None
    root = next((s for s in candidates if s.parent_span_id is None), candidates[0])
    attrs = root.attributes or {}
    raw_input = attrs.get(AgentAid.INPUT)
    raw_output = attrs.get(AgentAid.OUTPUT)
    return Run(
        id=root.run_id,
        agent_name=str(attrs.get(AgentAid.AGENT_NAME, "unknown")),
        started_at=root.started_at,
        ended_at=root.ended_at,
        status="succeeded" if root.ended_at else "running",
        prompt_sha=attrs.get(AgentAid.PROMPT_SHA),
        model=attrs.get(GenAI.RESPONSE_MODEL) or attrs.get(GenAI.REQUEST_MODEL),
        total_cost=float(attrs.get("agentaid.total_cost", 0.0) or 0.0),
        total_tokens=int(attrs.get(GenAI.USAGE_INPUT_TOKENS, 0) or 0)
                    + int(attrs.get(GenAI.USAGE_OUTPUT_TOKENS, 0) or 0),
        input=json.loads(raw_input) if isinstance(raw_input, str) else raw_input,
        output=json.loads(raw_output) if isinstance(raw_output, str) else raw_output,
    )
```

- [ ] **Step 4: Implement endpoint**

`packages/agentaid-server/src/agentaid_server/api/ingest.py`:

```python
from __future__ import annotations
from fastapi import APIRouter, status
from sqlmodel import select
from ..db.engine import SessionLocal
from ..db.models import Run, Span
from ..ingestion.parser import parse_span, derive_run

router = APIRouter()

@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest(payload: dict) -> dict[str, int]:
    raw_spans = payload.get("spans", [])
    parsed = [parse_span(r) for r in raw_spans]

    by_run: dict[str, list[Span]] = {}
    for s in parsed:
        if not s.run_id:
            continue
        by_run.setdefault(s.run_id, []).append(s)

    inserted_spans = 0
    upserted_runs = 0
    async with SessionLocal() as session:
        for run_id, spans in by_run.items():
            existing = (await session.exec(select(Run).where(Run.id == run_id))).first()
            if existing is None:
                derived = derive_run(spans)
                if derived is not None:
                    session.add(derived)
                    upserted_runs += 1
            else:
                # Update terminal timestamp / status if this batch contains the root.
                root = next((s for s in spans if s.parent_span_id is None), None)
                if root and root.ended_at:
                    existing.ended_at = root.ended_at
                    existing.status = "succeeded"
                    session.add(existing)
            for s in spans:
                # Upsert by id.
                in_db = await session.get(Span, s.id)
                if in_db is None:
                    session.add(s)
                    inserted_spans += 1
                else:
                    in_db.ended_at = s.ended_at
                    in_db.attributes = s.attributes
                    in_db.events = s.events
                    session.add(in_db)
        await session.commit()

    return {"runs": upserted_runs, "spans": inserted_spans}
```

`packages/agentaid-server/src/agentaid_server/api/__init__.py`:

```python
from . import ingest
__all__ = ["ingest"]
```

- [ ] **Step 5: Mount router in main.py**

In `packages/agentaid-server/src/agentaid_server/main.py`, after `app = FastAPI(...)` add:

```python
from .api import ingest as ingest_api
app.include_router(ingest_api.router)
```

- [ ] **Step 6: Run tests, expect PASS**

```bash
uv run pytest packages/agentaid-server/tests/test_ingest.py -v
```

- [ ] **Step 7: Commit and close**

```bash
git add packages/agentaid-server
git commit -m "add otel/genai ingestion endpoint"
bd close <id>
```

---

### Task 11: Read endpoints (runs/spans) + agent → server smoke

**Goal:** REST endpoints to list runs, fetch a run with its spans, and a manual smoke test confirming the reference agent (Task 8) can ship spans into a running server (Task 10) and the data is queryable.

**Files:**
- Create: `packages/agentaid-server/src/agentaid_server/api/runs.py`
- Modify: `packages/agentaid-server/src/agentaid_server/main.py` (mount runs router)
- Test: `packages/agentaid-server/tests/test_runs_api.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 11: runs/spans read api + agent->server smoke" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Failing test**

`packages/agentaid-server/tests/test_runs_api.py`:

```python
import pytest
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from sqlmodel import select
from agentaid_server.db.engine import SessionLocal, init_db
from agentaid_server.db.models import Run, Span

@pytest.fixture
async def app_with_data(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTAID_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'r.db'}")
    import importlib, agentaid_server.db.engine as eng, agentaid_server.main as mn
    importlib.reload(eng); importlib.reload(mn)
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
```

- [ ] **Step 3: Implement runs router**

`packages/agentaid-server/src/agentaid_server/api/runs.py`:

```python
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from sqlmodel import select
from ..db.engine import SessionLocal
from ..db.models import Run, Span

router = APIRouter()

@router.get("/runs")
async def list_runs(limit: int = 50, offset: int = 0,
                    agent_name: str | None = None) -> dict:
    async with SessionLocal() as s:
        stmt = select(Run).order_by(Run.started_at.desc()).limit(limit).offset(offset)
        if agent_name:
            stmt = stmt.where(Run.agent_name == agent_name)
        rows = (await s.exec(stmt)).all()
    return {"runs": [r.model_dump() for r in rows]}

@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    async with SessionLocal() as s:
        run = (await s.exec(select(Run).where(Run.id == run_id))).first()
        if run is None:
            raise HTTPException(404, f"run {run_id} not found")
        spans = (await s.exec(select(Span).where(Span.run_id == run_id)
                              .order_by(Span.started_at))).all()
    return {"run": run.model_dump(), "spans": [sp.model_dump() for sp in spans]}
```

- [ ] **Step 4: Mount in main.py**

Append to `main.py`:

```python
from .api import runs as runs_api
app.include_router(runs_api.router)
```

- [ ] **Step 5: Run tests, expect PASS**

```bash
uv run pytest packages/agentaid-server/tests/test_runs_api.py -v
```

- [ ] **Step 6: Manual end-to-end smoke (agent → server → query)**

In one terminal: `make server` (or `uv run uvicorn agentaid_server.main:app --port 8000`).
In another:

```bash
AGENTAID_ENDPOINT=http://localhost:8000/ingest uv run python -m arxiv_agent
sleep 2
curl -s http://localhost:8000/runs | python -m json.tool | head -30
```

Expected: a `runs` array with at least one entry with `agent_name == "arxiv-planner"`, and `GET /runs/<id>` returning a populated `spans` array.

- [ ] **Step 7: Commit and close**

```bash
git add packages/agentaid-server
git commit -m "add runs/spans read api"
bd close <id>
```

---

## Phase 4 — Frontend Foundation (Day 4, ~12h)

### Task 12: Vite + React + TS scaffold + routing + API client

**Goal:** A runnable Vite app at `packages/agentaid-web` with React Router for the seven planned routes, TanStack Query for server state, and a typed REST client whose response types match what the server returns.

**Files:**
- Create: `packages/agentaid-web/index.html`
- Create: `packages/agentaid-web/vite.config.ts`
- Create: `packages/agentaid-web/tsconfig.json`
- Create: `packages/agentaid-web/src/main.tsx`
- Create: `packages/agentaid-web/src/App.tsx`
- Create: `packages/agentaid-web/src/api/types.ts`
- Create: `packages/agentaid-web/src/api/client.ts`
- Create: `packages/agentaid-web/src/routes/{DriftHome,TraceDetail,RunComparison,DriftDetail,EvalResults,Datasets,RunList}.tsx` (stubs)
- Test: `packages/agentaid-web/src/api/client.test.ts`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 12: vite + react + ts scaffold + routing + api client" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: tsconfig and Vite config**

`packages/agentaid-web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "jsx": "react-jsx",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "allowImportingTsExtensions": false,
    "skipLibCheck": true,
    "types": ["vitest/globals"]
  },
  "include": ["src"]
}
```

`packages/agentaid-web/vite.config.ts`:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: true, rewrite: p => p.replace(/^\/api/, "") } },
  },
  test: { environment: "jsdom", globals: true, setupFiles: [] },
});
```

`packages/agentaid-web/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AgentAid</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 3: API types and client**

`packages/agentaid-web/src/api/types.ts`:

```typescript
export type RunStatus = "running" | "succeeded" | "failed";

export interface Run {
  id: string;
  agent_name: string;
  started_at: string;
  ended_at: string | null;
  status: RunStatus;
  prompt_sha: string | null;
  model: string | null;
  total_cost: number;
  total_tokens: number;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
}

export interface Span {
  id: string;
  run_id: string;
  parent_span_id: string | null;
  name: string;
  role: string | null;
  started_at: string;
  ended_at: string | null;
  attributes: Record<string, unknown>;
  events: Array<Record<string, unknown>>;
}

export interface RunDetail {
  run: Run;
  spans: Span[];
}

export interface RunsList {
  runs: Run[];
}

export type DriftSignal = "input" | "tool_call" | "quality";

export interface DriftState {
  signal: DriftSignal;
  detector_name: string;
  window: string;
  value: number;
  threshold: number;
  is_drifted: boolean;
  updated_at: string;
}
```

`packages/agentaid-web/src/api/client.ts`:

```typescript
import type { RunDetail, RunsList, DriftState } from "./types";

const BASE = "/api";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`);
  return res.json() as Promise<T>;
}

export const api = {
  listRuns: (params: { limit?: number; offset?: number } = {}): Promise<RunsList> => {
    const q = new URLSearchParams();
    if (params.limit !== undefined) q.set("limit", String(params.limit));
    if (params.offset !== undefined) q.set("offset", String(params.offset));
    const qs = q.toString();
    return getJson<RunsList>(`/runs${qs ? `?${qs}` : ""}`);
  },
  getRun: (id: string): Promise<RunDetail> => getJson<RunDetail>(`/runs/${id}`),
  driftState: (): Promise<{ signals: DriftState[] }> =>
    getJson<{ signals: DriftState[] }>(`/drift`),
};
```

- [ ] **Step 4: Failing test for the client**

`packages/agentaid-web/src/api/client.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "./client";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("api.listRuns", () => {
  it("hits /api/runs and returns parsed body", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ runs: [{ id: "r1" }] }), { status: 200 }),
    );
    const out = await api.listRuns({ limit: 10 });
    expect(fetchSpy).toHaveBeenCalledWith("/api/runs?limit=10");
    expect(out.runs[0].id).toBe("r1");
  });

  it("throws on non-2xx", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("nope", { status: 500, statusText: "Server Error" }),
    );
    await expect(api.listRuns()).rejects.toThrow(/500/);
  });
});
```

Run: `pnpm --filter agentaid-web test` → FAIL initially because the package isn't installed yet. After install, FAIL → PASS as you write code (the test code matches the impl above; expect PASS).

- [ ] **Step 5: App shell with routing**

`packages/agentaid-web/src/main.tsx`:

```typescript
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "./styles.css";

const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 5_000, refetchOnWindowFocus: false } } });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
```

`packages/agentaid-web/src/App.tsx`:

```typescript
import { Link, NavLink, Route, Routes } from "react-router-dom";
import DriftHome from "./routes/DriftHome";
import TraceDetail from "./routes/TraceDetail";
import RunComparison from "./routes/RunComparison";
import DriftDetail from "./routes/DriftDetail";
import EvalResults from "./routes/EvalResults";
import Datasets from "./routes/Datasets";
import RunList from "./routes/RunList";

const navItem = "px-3 py-2 hover:underline";

export default function App() {
  return (
    <div>
      <header className="border-b">
        <nav className="flex gap-1 px-4 py-2 items-center">
          <Link to="/" className="font-bold mr-4">AgentAid</Link>
          <NavLink to="/" className={navItem} end>Monitoring</NavLink>
          <NavLink to="/runs" className={navItem}>Traces</NavLink>
          <NavLink to="/evals" className={navItem}>Evals</NavLink>
          <NavLink to="/datasets" className={navItem}>Datasets</NavLink>
        </nav>
      </header>
      <main className="p-6">
        <Routes>
          <Route path="/" element={<DriftHome />} />
          <Route path="/runs" element={<RunList />} />
          <Route path="/runs/:id" element={<TraceDetail />} />
          <Route path="/compare" element={<RunComparison />} />
          <Route path="/drift/:signal" element={<DriftDetail />} />
          <Route path="/evals" element={<EvalResults />} />
          <Route path="/datasets" element={<Datasets />} />
        </Routes>
      </main>
    </div>
  );
}
```

`packages/agentaid-web/src/styles.css` (minimal):

```css
:root { color-scheme: light; font-family: ui-sans-serif, system-ui, sans-serif; }
* { box-sizing: border-box; }
body { margin: 0; }
.border-b { border-bottom: 1px solid #e5e7eb; }
.flex { display: flex; }
.gap-1 { gap: 0.25rem; }
.px-4 { padding-left: 1rem; padding-right: 1rem; }
.py-2 { padding-top: 0.5rem; padding-bottom: 0.5rem; }
.px-3 { padding-left: 0.75rem; padding-right: 0.75rem; }
.font-bold { font-weight: 700; }
.mr-4 { margin-right: 1rem; }
.p-6 { padding: 1.5rem; }
.items-center { align-items: center; }
```

- [ ] **Step 6: Stub route components**

For each of the seven routes, create a stub like `packages/agentaid-web/src/routes/DriftHome.tsx`:

```typescript
export default function DriftHome() {
  return <div><h1>Drift Home</h1><p>Coming in Task 13.</p></div>;
}
```

(Repeat for `TraceDetail.tsx`, `RunComparison.tsx`, `DriftDetail.tsx`, `EvalResults.tsx`, `Datasets.tsx`, `RunList.tsx`, each with a unique `<h1>`.)

- [ ] **Step 7: Install + run smoke**

```bash
pnpm install
pnpm --filter agentaid-web typecheck
pnpm --filter agentaid-web test
pnpm --filter agentaid-web build
```

Expected: type-check passes, vitest passes, build succeeds. Then:

```bash
pnpm --filter agentaid-web dev
```

Open http://localhost:5173 — see the `AgentAid` nav and the `DriftHome` stub.

- [ ] **Step 8: Commit and close**

```bash
git add packages/agentaid-web
git commit -m "scaffold vite/react/ts frontend with routing and api client"
bd close <id>
```

---

### Task 13: Drift-first home page (placeholder data first, live in Task 23)

**Goal:** Implement the home page with three drift signal cards and a recent-runs list. Data comes from real `/runs` endpoint (live) and a placeholder `/drift` endpoint (the live version lands in Task 21). Wire the card to whatever the `/drift` endpoint returns; if it's empty, show a "no data yet" state — that gracefully becomes live in Task 21 with no further frontend changes.

**Files:**
- Create: `packages/agentaid-web/src/components/DriftSignalCard.tsx`
- Create: `packages/agentaid-web/src/components/RunRow.tsx`
- Modify: `packages/agentaid-web/src/routes/DriftHome.tsx`
- Modify: `packages/agentaid-server/src/agentaid_server/api/drift.py` (placeholder endpoint)
- Modify: `packages/agentaid-server/src/agentaid_server/main.py` (mount drift router)
- Test: `packages/agentaid-web/src/routes/DriftHome.test.tsx`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 13: drift-first home page" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Server-side placeholder drift endpoint**

`packages/agentaid-server/src/agentaid_server/api/drift.py`:

```python
from __future__ import annotations
from fastapi import APIRouter
from sqlmodel import select
from ..db.engine import SessionLocal
from ..db.models import DriftStateRow

router = APIRouter()

@router.get("/drift")
async def drift_state() -> dict:
    async with SessionLocal() as s:
        rows = (await s.exec(select(DriftStateRow).order_by(DriftStateRow.updated_at.desc()))).all()
    # Pick the latest row per (signal, detector_name).
    latest: dict[tuple[str, str], DriftStateRow] = {}
    for r in rows:
        key = (r.signal, r.detector_name)
        if key not in latest or r.updated_at > latest[key].updated_at:
            latest[key] = r
    return {"signals": [r.model_dump() for r in latest.values()]}
```

Mount in `main.py`:

```python
from .api import drift as drift_api
app.include_router(drift_api.router)
```

- [ ] **Step 3: DriftSignalCard component**

`packages/agentaid-web/src/components/DriftSignalCard.tsx`:

```typescript
import type { DriftState, DriftSignal } from "../api/types";
import { Link } from "react-router-dom";

interface Props {
  signal: DriftSignal;
  state: DriftState | undefined;
}

const LABEL: Record<DriftSignal, string> = {
  input: "Input drift",
  tool_call: "Tool-call drift",
  quality: "Quality drift",
};

export default function DriftSignalCard({ signal, state }: Props) {
  const drifted = state?.is_drifted ?? false;
  const value = state?.value;
  return (
    <Link to={`/drift/${signal}`}
      style={{
        display: "block", padding: 16, border: "1px solid #e5e7eb",
        borderLeft: `4px solid ${drifted ? "#c0392b" : "#27ae60"}`,
        borderRadius: 6, textDecoration: "none", color: "inherit",
      }}>
      <div style={{ fontSize: 11, opacity: 0.7, textTransform: "uppercase" }}>{LABEL[signal]}</div>
      <div style={{ fontSize: 22, marginTop: 6, color: drifted ? "#c0392b" : "inherit" }}>
        {state ? <strong>{state.detector_name} {value?.toFixed(3)}</strong> : <span>—</span>}
      </div>
      <div style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>
        {state ? (drifted ? "▲ drifted" : "stable") : "no data yet"}
      </div>
    </Link>
  );
}
```

- [ ] **Step 4: RunRow component**

`packages/agentaid-web/src/components/RunRow.tsx`:

```typescript
import type { Run } from "../api/types";
import { Link } from "react-router-dom";

export default function RunRow({ run }: { run: Run }) {
  return (
    <Link to={`/runs/${run.id}`}
      style={{ display: "block", padding: 10, border: "1px solid #eee",
               fontFamily: "ui-monospace, monospace", fontSize: 12,
               textDecoration: "none", color: "inherit", marginBottom: 6 }}>
      {run.id} &nbsp;·&nbsp; {run.agent_name} &nbsp;·&nbsp; {run.status}
      &nbsp;·&nbsp; {run.total_tokens} tok &nbsp;·&nbsp; ${run.total_cost.toFixed(4)}
    </Link>
  );
}
```

- [ ] **Step 5: Implement DriftHome route**

`packages/agentaid-web/src/routes/DriftHome.tsx`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import DriftSignalCard from "../components/DriftSignalCard";
import RunRow from "../components/RunRow";
import type { DriftSignal, DriftState } from "../api/types";

const SIGNALS: DriftSignal[] = ["input", "tool_call", "quality"];

export default function DriftHome() {
  const drift = useQuery({ queryKey: ["drift"], queryFn: () => api.driftState(), refetchInterval: 5000 });
  const runs = useQuery({ queryKey: ["runs", { limit: 10 }], queryFn: () => api.listRuns({ limit: 10 }) });

  const stateBySignal = new Map<DriftSignal, DriftState>();
  for (const s of drift.data?.signals ?? []) stateBySignal.set(s.signal, s);

  return (
    <div>
      <div style={{ fontSize: 11, opacity: 0.7, textTransform: "uppercase", marginBottom: 8 }}>
        Drift signals · last 7 days
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 24 }}>
        {SIGNALS.map(s => <DriftSignalCard key={s} signal={s} state={stateBySignal.get(s)} />)}
      </div>
      <div style={{ fontSize: 11, opacity: 0.7, textTransform: "uppercase", marginBottom: 8 }}>
        Recent runs
      </div>
      {runs.isLoading && <div>Loading…</div>}
      {runs.data?.runs.map(r => <RunRow key={r.id} run={r} />)}
      {runs.data && runs.data.runs.length === 0 && <div style={{ opacity: 0.6 }}>No runs yet.</div>}
    </div>
  );
}
```

- [ ] **Step 6: Test for DriftHome**

`packages/agentaid-web/src/routes/DriftHome.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import DriftHome from "./DriftHome";

beforeEach(() => vi.restoreAllMocks());

function renderHome() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter><DriftHome /></MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DriftHome", () => {
  it("shows three drift signal cards labeled correctly", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
      const u = String(url);
      if (u.includes("/drift")) return new Response(JSON.stringify({ signals: [] }), { status: 200 });
      if (u.includes("/runs")) return new Response(JSON.stringify({ runs: [] }), { status: 200 });
      return new Response("not found", { status: 404 });
    });
    renderHome();
    await waitFor(() => expect(screen.getByText("Input drift")).toBeInTheDocument());
    expect(screen.getByText("Tool-call drift")).toBeInTheDocument();
    expect(screen.getByText("Quality drift")).toBeInTheDocument();
  });
});
```

(Add `@testing-library/jest-dom` and import it in a setup file if `toBeInTheDocument` is used — or use plain DOM checks like `screen.queryByText("…") !== null`.)

- [ ] **Step 7: Run tests + smoke**

```bash
pnpm --filter agentaid-web test
pnpm --filter agentaid-web dev
```

Expected: tests pass; opening http://localhost:5173 shows three "no data yet" drift cards and a recent-runs list (populated if the server has had runs ingested).

- [ ] **Step 8: Commit and close**

```bash
git add packages/agentaid-web packages/agentaid-server
git commit -m "implement drift-first home page and placeholder /drift endpoint"
bd close <id>
```

---

### Task 14: Trace detail Gantt page

**Goal:** Implement the trace detail view at `/runs/:id` with a Gantt timeline of spans (planner + workers + tool calls), drift contribution band at the top, span detail callout when a bar is clicked. Multi-modal figure spans render their image attribute inline.

**Files:**
- Create: `packages/agentaid-web/src/components/GanttChart.tsx`
- Modify: `packages/agentaid-web/src/routes/TraceDetail.tsx`
- Test: `packages/agentaid-web/src/components/GanttChart.test.tsx`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 14: trace detail gantt page" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Failing test**

`packages/agentaid-web/src/components/GanttChart.test.tsx`:

```typescript
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import GanttChart, { type GanttSpan } from "./GanttChart";

const spans: GanttSpan[] = [
  { id: "p", parentId: null, name: "planner", role: "planner",
    start: 0, end: 10, durationLabel: "10s" },
  { id: "w1", parentId: "p", name: "worker", role: "worker",
    start: 2, end: 6, durationLabel: "4s" },
];

describe("GanttChart", () => {
  it("renders a row per span with proportional bars", () => {
    const { container } = render(<GanttChart spans={spans} />);
    const bars = container.querySelectorAll("[data-test='gantt-bar']");
    expect(bars.length).toBe(2);
  });

  it("calls onSpanClick with span id", () => {
    let clicked = "";
    const { container } = render(<GanttChart spans={spans} onSpanClick={(id) => (clicked = id)} />);
    const bar = container.querySelectorAll("[data-test='gantt-bar']")[0] as HTMLElement;
    bar.click();
    expect(clicked).toBe("p");
  });
});
```

- [ ] **Step 3: Implement GanttChart**

`packages/agentaid-web/src/components/GanttChart.tsx`:

```typescript
export interface GanttSpan {
  id: string;
  parentId: string | null;
  name: string;
  role: string | null;
  start: number;          // ms or s, relative to run start (any unit, normalized internally)
  end: number;
  durationLabel: string;
}

interface Props {
  spans: GanttSpan[];
  onSpanClick?: (id: string) => void;
  highlightId?: string;
}

const ROLE_COLORS: Record<string, string> = {
  planner: "#4a90e2",
  worker: "#7bb86b",
  tool: "#c8b04a",
};

export default function GanttChart({ spans, onSpanClick, highlightId }: Props) {
  if (spans.length === 0) return <div style={{ opacity: 0.6 }}>No spans.</div>;
  const min = Math.min(...spans.map(s => s.start));
  const max = Math.max(...spans.map(s => s.end));
  const total = Math.max(1, max - min);

  return (
    <div style={{ fontFamily: "ui-monospace, monospace", fontSize: 11 }}>
      {spans.map((s) => {
        const left = ((s.start - min) / total) * 100;
        const width = Math.max(0.5, ((s.end - s.start) / total) * 100);
        const color = ROLE_COLORS[s.role ?? ""] ?? "#888";
        const indent = s.parentId ? 16 : 0;
        return (
          <div key={s.id}
            style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <div style={{ width: 140, paddingLeft: indent, textAlign: "right" }}>
              {s.role ? `${s.role} · ${s.name}` : s.name}
            </div>
            <div style={{ flex: 1, height: 18, background: "#eee", position: "relative" }}>
              <div data-test="gantt-bar"
                onClick={() => onSpanClick?.(s.id)}
                style={{
                  position: "absolute",
                  left: `${left}%`,
                  width: `${width}%`,
                  height: "100%",
                  background: color,
                  outline: highlightId === s.id ? "2px solid #c0392b" : "none",
                  cursor: "pointer",
                }} />
            </div>
            <div style={{ width: 60, textAlign: "right", opacity: 0.7 }}>{s.durationLabel}</div>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Implement TraceDetail route**

`packages/agentaid-web/src/routes/TraceDetail.tsx`:

```typescript
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import GanttChart, { type GanttSpan } from "../components/GanttChart";
import type { Span } from "../api/types";

function toGanttSpans(spans: Span[]): GanttSpan[] {
  if (spans.length === 0) return [];
  const t0 = Math.min(...spans.map(s => Date.parse(s.started_at)));
  return spans.map(s => {
    const start = Date.parse(s.started_at) - t0;
    const end = s.ended_at ? Date.parse(s.ended_at) - t0 : start;
    return {
      id: s.id, parentId: s.parent_span_id, name: s.name, role: s.role,
      start, end,
      durationLabel: `${((end - start) / 1000).toFixed(2)}s`,
    };
  });
}

export default function TraceDetail() {
  const { id = "" } = useParams();
  const [selected, setSelected] = useState<string | null>(null);
  const detail = useQuery({ queryKey: ["run", id], queryFn: () => api.getRun(id), enabled: Boolean(id) });

  if (detail.isLoading) return <div>Loading…</div>;
  if (detail.isError || !detail.data) return <div>Run not found.</div>;

  const { run, spans } = detail.data;
  const gantt = toGanttSpans(spans);
  const sel = spans.find(s => s.id === selected);

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <strong>{run.id}</strong> · {run.agent_name} · {run.status} · {run.total_tokens} tok · ${run.total_cost.toFixed(4)}
      </div>
      <div style={{ background: "#f7f7f7", padding: 8, marginBottom: 12, fontSize: 11, opacity: 0.85 }}>
        DRIFT CONTRIBUTION · (live in Task 23)
      </div>
      <GanttChart spans={gantt} onSpanClick={setSelected} highlightId={selected ?? undefined} />
      {sel && (
        <div style={{ marginTop: 16, padding: 12, border: "1px solid #ddd" }}>
          <div style={{ fontSize: 10, opacity: 0.7 }}>SELECTED · {sel.role ?? "—"} / {sel.name}</div>
          <pre style={{ background: "#f5f5f5", padding: 8, fontSize: 11, overflow: "auto" }}>
            {JSON.stringify(sel.attributes, null, 2)}
          </pre>
          {sel.attributes["agentaid.figure_data_url"] && (
            <img src={String(sel.attributes["agentaid.figure_data_url"])} alt="figure"
                 style={{ maxWidth: 600, marginTop: 8 }} />
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Run tests + smoke**

```bash
pnpm --filter agentaid-web test
pnpm --filter agentaid-web dev
```

Open http://localhost:5173/runs/<some-run-id> with a server populated from Task 11's smoke. Verify Gantt rows render and clicking a bar surfaces span attributes.

- [ ] **Step 6: Commit and close**

```bash
git add packages/agentaid-web
git commit -m "implement trace detail gantt page"
bd close <id>
```

---

## Phase 5 — Eval Framework (Day 5, ~12h)

### Task 15: Eval definition decorator + registry + LLM judge helper

**Goal:** Implement `@agentaid.eval` and a registry the server discovers evals through. Plus a `llm_judge` helper that produces an `EvalResult` with score + rationale via an Anthropic call.

**Files:**
- Create: `packages/agentaid-py/src/agentaid/eval/__init__.py`
- Create: `packages/agentaid-py/src/agentaid/eval/decorator.py`
- Create: `packages/agentaid-py/src/agentaid/eval/registry.py`
- Create: `packages/agentaid-py/src/agentaid/eval/judge.py`
- Test: `packages/agentaid-py/tests/test_eval_decorator.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 15: eval decorator + registry + judge helper" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Failing test**

`packages/agentaid-py/tests/test_eval_decorator.py`:

```python
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
    with pytest.raises(ValueError):
        @agentaid_eval(name="t_sum_present", mode=EvalMode.INVARIANT)
        async def dup(run: Run, golden: Golden | None = None) -> EvalResult:
            raise NotImplementedError
```

Run: `uv run pytest packages/agentaid-py/tests/test_eval_decorator.py -v` → FAIL.

- [ ] **Step 3: Implement registry**

`packages/agentaid-py/src/agentaid/eval/registry.py`:

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Awaitable, Callable
from agentaid.models import EvalMode, EvalResult, Run, Golden

EvalFn = Callable[[Run, Golden | None], Awaitable[EvalResult]]

@dataclass(frozen=True)
class EvalSpec:
    name: str
    mode: EvalMode
    fn: EvalFn
    judge_model: str | None = None

_REGISTRY: dict[str, EvalSpec] = {}

def register(spec: EvalSpec) -> None:
    if spec.name in _REGISTRY:
        raise ValueError(f"eval '{spec.name}' is already registered")
    _REGISTRY[spec.name] = spec

def get_eval(name: str) -> EvalSpec:
    return _REGISTRY[name]

def list_evals() -> list[str]:
    return sorted(_REGISTRY.keys())

def evals_for_mode(mode: EvalMode) -> list[EvalSpec]:
    return [s for s in _REGISTRY.values() if s.mode == mode]

def reset_for_tests() -> None:
    _REGISTRY.clear()
```

- [ ] **Step 4: Implement decorator**

`packages/agentaid-py/src/agentaid/eval/decorator.py`:

```python
from __future__ import annotations
from agentaid.models import EvalMode
from .registry import EvalFn, EvalSpec, register

def eval(*, name: str, mode: EvalMode, judge_model: str | None = None):
    def decorator(fn: EvalFn) -> EvalFn:
        register(EvalSpec(name=name, mode=mode, fn=fn, judge_model=judge_model))
        return fn
    return decorator
```

- [ ] **Step 5: Implement LLM judge helper**

`packages/agentaid-py/src/agentaid/eval/judge.py`:

```python
from __future__ import annotations
import json
from anthropic import AsyncAnthropic
from agentaid.models import EvalResult, EvalMode

_client: AsyncAnthropic | None = None

def _get() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic()
    return _client

async def llm_judge(*, instructions: str, run_input: str, run_output: str,
                   model: str = "claude-haiku-4-5", run_id: str,
                   eval_name: str, mode: EvalMode = EvalMode.ONLINE) -> EvalResult:
    """Score an output against an instruction. Returns 0..1 + rationale."""
    prompt = (
        f"{instructions}\n\n"
        f"Input given to the system:\n{run_input}\n\n"
        f"System output:\n{run_output}\n\n"
        "Return a single JSON object with fields:\n"
        "  score: float in [0, 1]\n"
        "  label: short tag string\n"
        "  rationale: one or two sentences\n"
        "No prose outside the JSON."
    )
    msg = await _get().messages.create(
        model=model, max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if b.type == "text")
    s, e = text.find("{"), text.rfind("}")
    data = json.loads(text[s:e + 1])
    return EvalResult(
        run_id=run_id, eval_name=eval_name, mode=mode,
        score=float(max(0.0, min(1.0, data["score"]))),
        label=str(data.get("label", "")),
        rationale=str(data.get("rationale", "")),
    )
```

`packages/agentaid-py/src/agentaid/eval/__init__.py`:

```python
from .decorator import eval
from .judge import llm_judge
from . import registry, templates

__all__ = ["eval", "llm_judge", "registry", "templates"]
```

- [ ] **Step 6: Run tests, expect PASS**

```bash
uv run pytest packages/agentaid-py/tests/test_eval_decorator.py -v
```

(The test mutates the global registry. Add a `conftest.py` autouse fixture calling `registry.reset_for_tests()` before each test if needed across the eval test suite.)

- [ ] **Step 7: Commit and close**

```bash
git add packages/agentaid-py
git commit -m "add eval decorator, registry, and llm judge helper"
bd close <id>
```

---

### Task 16: Built-in eval templates (4)

**Goal:** Ship `relevance_judge`, `faithfulness_judge`, `structural_completeness`, `cost_within_budget`. Two are LLM-judges (online), two are invariants. All registered via `@agentaid.eval` so the server picks them up at import time.

**Files:**
- Create: `packages/agentaid-py/src/agentaid/eval/templates/__init__.py`
- Create: `packages/agentaid-py/src/agentaid/eval/templates/relevance_judge.py`
- Create: `packages/agentaid-py/src/agentaid/eval/templates/faithfulness_judge.py`
- Create: `packages/agentaid-py/src/agentaid/eval/templates/structural_completeness.py`
- Create: `packages/agentaid-py/src/agentaid/eval/templates/cost_within_budget.py`
- Test: `packages/agentaid-py/tests/test_eval_templates.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 16: 4 built-in eval templates" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Failing tests**

`packages/agentaid-py/tests/test_eval_templates.py`:

```python
import pytest
from datetime import datetime
from agentaid.models import Run, EvalMode
from agentaid.eval import registry
from agentaid.eval import templates  # noqa: F401  -- triggers registration

@pytest.fixture(autouse=True)
def _reset() -> None:
    registry.reset_for_tests()
    # Re-import to re-register.
    import importlib, agentaid.eval.templates as t
    for sub in ("relevance_judge", "faithfulness_judge",
                "structural_completeness", "cost_within_budget"):
        importlib.reload(__import__(f"agentaid.eval.templates.{sub}", fromlist=[sub]))

def test_all_four_registered() -> None:
    names = set(registry.list_evals())
    assert {"relevance_judge", "faithfulness_judge",
            "structural_completeness", "cost_within_budget"} <= names

@pytest.mark.asyncio
async def test_structural_completeness_passes_when_digest_complete() -> None:
    run = Run(id="r1", agent_name="a", started_at=datetime.utcnow(),
              output={"digest": "## P1\n- summary\n- score: 0.9\n[citation: 2401.00001]"})
    spec = registry.get_eval("structural_completeness")
    res = await spec.fn(run, None)
    assert res.score == 1.0

@pytest.mark.asyncio
async def test_structural_completeness_fails_when_digest_empty() -> None:
    run = Run(id="r1", agent_name="a", started_at=datetime.utcnow(), output={"digest": ""})
    spec = registry.get_eval("structural_completeness")
    res = await spec.fn(run, None)
    assert res.score == 0.0

@pytest.mark.asyncio
async def test_cost_within_budget_score() -> None:
    spec = registry.get_eval("cost_within_budget")
    cheap = Run(id="r-cheap", agent_name="a", started_at=datetime.utcnow(), total_cost=0.05)
    expensive = Run(id="r-expensive", agent_name="a", started_at=datetime.utcnow(), total_cost=2.0)
    assert (await spec.fn(cheap, None)).score == 1.0
    assert (await spec.fn(expensive, None)).score < 1.0
```

Run: `uv run pytest packages/agentaid-py/tests/test_eval_templates.py -v` → FAIL.

- [ ] **Step 3: Implement structural_completeness (invariant)**

`packages/agentaid-py/src/agentaid/eval/templates/structural_completeness.py`:

```python
from __future__ import annotations
import re
from agentaid.models import EvalMode, EvalResult, Run, Golden
from ..decorator import eval as agentaid_eval

@agentaid_eval(name="structural_completeness", mode=EvalMode.INVARIANT)
async def structural_completeness(run: Run, golden: Golden | None = None) -> EvalResult:
    digest = (run.output or {}).get("digest") if run.output else None
    if not isinstance(digest, str) or not digest.strip():
        return EvalResult(run_id=run.id, eval_name="structural_completeness",
                          mode=EvalMode.INVARIANT, score=0.0,
                          label="empty",
                          rationale="digest is missing or empty")
    sections = len(re.findall(r"^##\s+", digest, flags=re.M))
    has_summary = "summary" in digest.lower() or re.search(r"^- ", digest, flags=re.M)
    has_citation = bool(re.search(r"\d{4}\.\d{4,5}", digest))
    score = 1.0 if sections >= 1 and has_summary and has_citation else 0.5 if sections else 0.0
    return EvalResult(run_id=run.id, eval_name="structural_completeness",
                      mode=EvalMode.INVARIANT, score=score,
                      label=f"sections={sections}",
                      rationale="checked section headers, bullet summaries, and citation format")
```

- [ ] **Step 4: Implement cost_within_budget (invariant)**

`packages/agentaid-py/src/agentaid/eval/templates/cost_within_budget.py`:

```python
from __future__ import annotations
import os
from agentaid.models import EvalMode, EvalResult, Run, Golden
from ..decorator import eval as agentaid_eval

DEFAULT_BUDGET = float(os.getenv("AGENTAID_COST_BUDGET_USD", "0.50"))

@agentaid_eval(name="cost_within_budget", mode=EvalMode.INVARIANT)
async def cost_within_budget(run: Run, golden: Golden | None = None) -> EvalResult:
    cost = run.total_cost
    if cost <= DEFAULT_BUDGET:
        score = 1.0
        label = "within"
    elif cost <= DEFAULT_BUDGET * 2:
        score = 0.5
        label = "exceeded"
    else:
        score = 0.0
        label = "blown"
    return EvalResult(run_id=run.id, eval_name="cost_within_budget",
                      mode=EvalMode.INVARIANT, score=score, label=label,
                      rationale=f"cost ${cost:.4f} vs budget ${DEFAULT_BUDGET:.2f}")
```

- [ ] **Step 5: Implement relevance_judge (online LLM)**

`packages/agentaid-py/src/agentaid/eval/templates/relevance_judge.py`:

```python
from __future__ import annotations
import json
from agentaid.models import EvalMode, EvalResult, Run, Golden
from ..decorator import eval as agentaid_eval
from ..judge import llm_judge

@agentaid_eval(name="relevance_judge", mode=EvalMode.ONLINE, judge_model="claude-haiku-4-5")
async def relevance_judge(run: Run, golden: Golden | None = None) -> EvalResult:
    inp = (run.input or {}).get("research_interest") if run.input else None
    out = (run.output or {}).get("digest") if run.output else None
    if not inp or not out:
        return EvalResult(run_id=run.id, eval_name="relevance_judge",
                          mode=EvalMode.ONLINE, score=0.0,
                          label="missing", rationale="input or output not present")
    return await llm_judge(
        instructions=("Score 0..1 how well the research digest matches the requested research interest. "
                      "Penalize off-topic papers, generic restatements, or thin coverage."),
        run_input=str(inp),
        run_output=str(out)[:5000],
        model="claude-haiku-4-5",
        run_id=run.id, eval_name="relevance_judge",
    )
```

- [ ] **Step 6: Implement faithfulness_judge (online LLM)**

`packages/agentaid-py/src/agentaid/eval/templates/faithfulness_judge.py`:

```python
from __future__ import annotations
import json
from agentaid.models import EvalMode, EvalResult, Run, Golden
from ..decorator import eval as agentaid_eval
from ..judge import llm_judge

@agentaid_eval(name="faithfulness_judge", mode=EvalMode.ONLINE, judge_model="claude-haiku-4-5")
async def faithfulness_judge(run: Run, golden: Golden | None = None) -> EvalResult:
    out = (run.output or {}).get("digest") if run.output else None
    sections = (run.output or {}).get("sections") if run.output else None
    if not out:
        return EvalResult(run_id=run.id, eval_name="faithfulness_judge",
                          mode=EvalMode.ONLINE, score=0.0,
                          label="missing", rationale="no digest")
    src = json.dumps(sections) if sections else "(no per-paper sections recorded)"
    return await llm_judge(
        instructions=("Score 0..1 how faithful the digest is to the per-paper summaries provided. "
                      "Penalize hallucinated facts, claims not present in the source summaries, "
                      "or numerical drift."),
        run_input=src,
        run_output=str(out)[:5000],
        model="claude-haiku-4-5",
        run_id=run.id, eval_name="faithfulness_judge",
    )
```

- [ ] **Step 7: Templates package init**

`packages/agentaid-py/src/agentaid/eval/templates/__init__.py`:

```python
# Importing each module triggers @agentaid.eval registration.
from . import structural_completeness  # noqa: F401
from . import cost_within_budget       # noqa: F401
from . import relevance_judge          # noqa: F401
from . import faithfulness_judge       # noqa: F401
```

- [ ] **Step 8: Run tests, expect PASS**

```bash
uv run pytest packages/agentaid-py/tests/test_eval_templates.py -v
```

- [ ] **Step 9: Commit and close**

```bash
git add packages/agentaid-py
git commit -m "add 4 built-in eval templates"
bd close <id>
```

---

### Task 17: Server-side eval orchestrator (Mode 1 + Mode 3)

**Goal:** Server discovers registered evals on import, runs Mode 3 invariants synchronously after a run finalizes, and runs Mode 1 LLM-judges async (background task). Writes `EvalResult` rows. Adds `/runs/{id}/evals` endpoint to read them.

**Files:**
- Create: `packages/agentaid-server/src/agentaid_server/orchestrator/__init__.py`
- Create: `packages/agentaid-server/src/agentaid_server/orchestrator/eval_runner.py`
- Modify: `packages/agentaid-server/src/agentaid_server/api/ingest.py` (kick off eval runner when a run terminates)
- Create: `packages/agentaid-server/src/agentaid_server/api/evals.py`
- Modify: `packages/agentaid-server/src/agentaid_server/main.py`
- Test: `packages/agentaid-server/tests/test_eval_runner.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 17: server eval orchestrator (mode 1 + mode 3)" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Failing test**

`packages/agentaid-server/tests/test_eval_runner.py`:

```python
import pytest
from datetime import datetime
from sqlmodel import select
from agentaid_server.orchestrator.eval_runner import run_invariants, run_online
from agentaid_server.db.engine import SessionLocal, init_db
from agentaid_server.db.models import Run, EvalResult

@pytest.mark.asyncio
async def test_run_invariants_writes_results(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTAID_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'e.db'}")
    import importlib, agentaid_server.db.engine as eng
    importlib.reload(eng)
    await init_db()
    async with SessionLocal() as s:
        s.add(Run(id="rx", agent_name="a", started_at=datetime.utcnow(),
                  ended_at=datetime.utcnow(), status="succeeded", total_cost=0.01,
                  output={"digest": "## p\n- s\n2401.00001"}))
        await s.commit()

    await run_invariants("rx")
    async with SessionLocal() as s:
        rows = (await s.exec(select(EvalResult).where(EvalResult.run_id == "rx"))).all()
    names = {r.eval_name for r in rows}
    assert "structural_completeness" in names
    assert "cost_within_budget" in names
```

Run: `uv run pytest packages/agentaid-server/tests/test_eval_runner.py -v` → FAIL.

- [ ] **Step 3: Implement orchestrator**

`packages/agentaid-server/src/agentaid_server/orchestrator/eval_runner.py`:

```python
from __future__ import annotations
import asyncio
import logging
import random
from sqlmodel import select
from agentaid.eval import registry
from agentaid.eval import templates  # noqa: F401  -- import triggers registration
from agentaid.models import EvalMode, Run as RunModel, EvalResult as DomainEval
from ..config import settings
from ..db.engine import SessionLocal
from ..db.models import Run, EvalResult

log = logging.getLogger(__name__)

def _to_domain(run: Run) -> RunModel:
    return RunModel(
        id=run.id, agent_name=run.agent_name, started_at=run.started_at,
        ended_at=run.ended_at, input=run.input, output=run.output,
        prompt_sha=run.prompt_sha, model=run.model,
        total_cost=run.total_cost, total_tokens=run.total_tokens,
        status=run.status,  # type: ignore[arg-type]
    )

async def _persist(result: DomainEval) -> None:
    async with SessionLocal() as s:
        s.add(EvalResult(
            run_id=result.run_id, eval_name=result.eval_name,
            mode=result.mode.value, score=result.score,
            label=result.label, rationale=result.rationale,
        ))
        await s.commit()

async def run_invariants(run_id: str) -> None:
    async with SessionLocal() as s:
        run = (await s.exec(select(Run).where(Run.id == run_id))).first()
    if run is None:
        log.warning("run %s not found for invariants", run_id)
        return
    domain = _to_domain(run)
    for spec in registry.evals_for_mode(EvalMode.INVARIANT):
        try:
            res = await spec.fn(domain, None)
            await _persist(res)
        except Exception:
            log.exception("invariant eval %s failed for run %s", spec.name, run_id)

async def run_online(run_id: str) -> None:
    if random.random() > settings.online_eval_sample_rate:
        return
    async with SessionLocal() as s:
        run = (await s.exec(select(Run).where(Run.id == run_id))).first()
    if run is None:
        return
    domain = _to_domain(run)
    tasks = []
    for spec in registry.evals_for_mode(EvalMode.ONLINE):
        tasks.append(asyncio.create_task(_run_one(spec, domain)))
    await asyncio.gather(*tasks, return_exceptions=True)

async def _run_one(spec, domain: RunModel) -> None:
    try:
        res = await spec.fn(domain, None)
        await _persist(res)
    except Exception:
        log.exception("online eval %s failed for run %s", spec.name, domain.id)
```

`packages/agentaid-server/src/agentaid_server/orchestrator/__init__.py`:

```python
from .eval_runner import run_invariants, run_online
__all__ = ["run_invariants", "run_online"]
```

- [ ] **Step 4: Hook into ingestion**

Replace `packages/agentaid-server/src/agentaid_server/api/ingest.py` with the full updated version (extends Task 10's endpoint with background eval scheduling):

```python
from __future__ import annotations
from fastapi import APIRouter, BackgroundTasks, status
from sqlmodel import select
from ..db.engine import SessionLocal
from ..db.models import Run, Span
from ..ingestion.parser import parse_span, derive_run
from ..orchestrator import run_invariants, run_online

router = APIRouter()

@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest(payload: dict, bg: BackgroundTasks) -> dict[str, int]:
    raw_spans = payload.get("spans", [])
    parsed = [parse_span(r) for r in raw_spans]

    by_run: dict[str, list[Span]] = {}
    for s in parsed:
        if not s.run_id:
            continue
        by_run.setdefault(s.run_id, []).append(s)

    inserted_spans = 0
    upserted_runs = 0
    async with SessionLocal() as session:
        for run_id, spans in by_run.items():
            existing = (await session.exec(select(Run).where(Run.id == run_id))).first()
            if existing is None:
                derived = derive_run(spans)
                if derived is not None:
                    session.add(derived)
                    upserted_runs += 1
            else:
                root = next((s for s in spans if s.parent_span_id is None), None)
                if root and root.ended_at:
                    existing.ended_at = root.ended_at
                    existing.status = "succeeded"
                    session.add(existing)
            for s in spans:
                in_db = await session.get(Span, s.id)
                if in_db is None:
                    session.add(s)
                    inserted_spans += 1
                else:
                    in_db.ended_at = s.ended_at
                    in_db.attributes = s.attributes
                    in_db.events = s.events
                    session.add(in_db)
        await session.commit()

    # Schedule evals for runs that terminated in this batch.
    for run_id, spans in by_run.items():
        if any(sp.parent_span_id is None and sp.ended_at for sp in spans):
            bg.add_task(run_invariants, run_id)
            bg.add_task(run_online, run_id)

    return {"runs": upserted_runs, "spans": inserted_spans}
```

- [ ] **Step 5: Eval read endpoint**

`packages/agentaid-server/src/agentaid_server/api/evals.py`:

```python
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from sqlmodel import select
from ..db.engine import SessionLocal
from ..db.models import EvalResult

router = APIRouter()

@router.get("/runs/{run_id}/evals")
async def evals_for_run(run_id: str) -> dict:
    async with SessionLocal() as s:
        rows = (await s.exec(select(EvalResult).where(EvalResult.run_id == run_id))).all()
    return {"results": [r.model_dump() for r in rows]}

@router.get("/evals/recent")
async def recent_evals(eval_name: str | None = None, limit: int = 100) -> dict:
    async with SessionLocal() as s:
        stmt = select(EvalResult).order_by(EvalResult.created_at.desc()).limit(limit)
        if eval_name:
            stmt = stmt.where(EvalResult.eval_name == eval_name)
        rows = (await s.exec(stmt)).all()
    return {"results": [r.model_dump() for r in rows]}
```

Mount in `main.py`:

```python
from .api import evals as evals_api
app.include_router(evals_api.router)
```

- [ ] **Step 6: Run tests, expect PASS**

```bash
uv run pytest packages/agentaid-server/tests/test_eval_runner.py -v
```

- [ ] **Step 7: Smoke (optional, costs Anthropic tokens)**

Trigger an agent run via Task 11's smoke. After ingestion settles, query:

```bash
curl -s http://localhost:8000/runs/<run_id>/evals
```

Expected: includes `structural_completeness` and `cost_within_budget` results immediately, and `relevance_judge` / `faithfulness_judge` after a few seconds (online evals are async).

- [ ] **Step 8: Commit and close**

```bash
git add packages/agentaid-server
git commit -m "add eval orchestrator with mode 1/3 dispatch and read endpoints"
bd close <id>
```

---

### Task 18: Eval results page (frontend)

**Goal:** Implement `/evals` route showing recent eval results across all runs in a table, plus per-run drilldown via existing `/runs/:id`. Add a per-eval sparkline using `recharts`.

**Files:**
- Modify: `packages/agentaid-web/src/api/types.ts` (add `EvalResult`)
- Modify: `packages/agentaid-web/src/api/client.ts` (add `evalsRecent`)
- Modify: `packages/agentaid-web/src/routes/EvalResults.tsx`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 18: eval results page" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Add types**

In `packages/agentaid-web/src/api/types.ts`, append:

```typescript
export type EvalMode = "online" | "regression" | "invariant";

export interface EvalResult {
  run_id: string;
  eval_name: string;
  mode: EvalMode;
  score: number;
  label: string | null;
  rationale: string | null;
  created_at: string;
}
```

- [ ] **Step 3: Add client method**

In `packages/agentaid-web/src/api/client.ts`, append to the `api` object:

```typescript
  evalsRecent: (params: { evalName?: string; limit?: number } = {}): Promise<{ results: EvalResult[] }> => {
    const q = new URLSearchParams();
    if (params.evalName) q.set("eval_name", params.evalName);
    if (params.limit !== undefined) q.set("limit", String(params.limit));
    const qs = q.toString();
    return getJson<{ results: EvalResult[] }>(`/evals/recent${qs ? `?${qs}` : ""}`);
  },
```

(And import the `EvalResult` type at the top of `client.ts`.)

- [ ] **Step 4: Implement EvalResults route**

`packages/agentaid-web/src/routes/EvalResults.tsx`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";
import { api } from "../api/client";
import type { EvalResult } from "../api/types";

const NAMES = ["relevance_judge", "faithfulness_judge", "structural_completeness", "cost_within_budget"];

export default function EvalResults() {
  const queries = NAMES.map((name) =>
    useQuery({ queryKey: ["evals", name], queryFn: () => api.evalsRecent({ evalName: name, limit: 50 }) }),
  );
  return (
    <div>
      <h2>Eval results</h2>
      {NAMES.map((name, i) => {
        const data = queries[i].data?.results ?? [];
        const series = [...data].reverse().map((r, idx) => ({ idx, score: r.score }));
        const latest = data[0];
        return (
          <section key={name} style={{ marginBottom: 24, border: "1px solid #eee", padding: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <div><strong>{name}</strong> · n={data.length}</div>
              <div>latest: {latest ? latest.score.toFixed(3) : "—"}</div>
            </div>
            <div style={{ height: 100, marginTop: 8 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={series}>
                  <XAxis dataKey="idx" hide />
                  <YAxis domain={[0, 1]} width={32} />
                  <Tooltip />
                  <Line dataKey="score" dot={false} stroke="#4a90e2" />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div style={{ marginTop: 8, fontFamily: "ui-monospace, monospace", fontSize: 11 }}>
              {data.slice(0, 5).map((r) => (
                <Link key={`${r.run_id}-${r.eval_name}-${r.created_at}`}
                  to={`/runs/${r.run_id}`}
                  style={{ display: "block", textDecoration: "none", color: "inherit" }}>
                  {r.created_at} · {r.run_id} · {r.score.toFixed(3)}{r.label ? ` · ${r.label}` : ""}
                </Link>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 5: Type-check + smoke**

```bash
pnpm --filter agentaid-web typecheck
pnpm --filter agentaid-web dev
```

Open `/evals` — expect four panels with sparklines (empty initially, populated after agent runs complete).

- [ ] **Step 6: Commit and close**

```bash
git add packages/agentaid-web
git commit -m "implement eval results page with sparklines"
bd close <id>
```

---

## Phase 6 — Drift Detection (Day 6, ~12h)

### Task 19: DriftDetector protocol + ADWIN implementation

**Goal:** A clean `DriftDetector` Protocol and a hand-rolled ADWIN implementation. Hand-rolling rather than depending on `scikit-multiflow` to (a) demonstrate the math and (b) avoid a heavy dependency for ~150 LOC.

**Files:**
- Create: `packages/agentaid-py/src/agentaid/drift/__init__.py`
- Create: `packages/agentaid-py/src/agentaid/drift/protocol.py`
- Create: `packages/agentaid-py/src/agentaid/drift/adwin.py`
- Test: `packages/agentaid-py/tests/test_drift_adwin.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 19: drift protocol + adwin detector" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Failing test**

`packages/agentaid-py/tests/test_drift_adwin.py`:

```python
import random
from agentaid.drift.adwin import ADWIN

def test_adwin_does_not_fire_on_stationary_stream() -> None:
    random.seed(0)
    a = ADWIN(delta=0.002)
    fired = False
    for _ in range(2000):
        if a.update(random.gauss(0.7, 0.05)):
            fired = True
            break
    assert not fired, "ADWIN should not fire on stationary stream"

def test_adwin_fires_on_mean_shift() -> None:
    random.seed(1)
    a = ADWIN(delta=0.002)
    fired_at = None
    for i in range(2000):
        v = random.gauss(0.8, 0.05) if i < 800 else random.gauss(0.4, 0.05)
        if a.update(v) and fired_at is None:
            fired_at = i
    assert fired_at is not None
    assert 800 < fired_at < 1300, f"fired at {fired_at}"
```

Run: `uv run pytest packages/agentaid-py/tests/test_drift_adwin.py -v` → FAIL.

- [ ] **Step 3: Protocol**

`packages/agentaid-py/src/agentaid/drift/protocol.py`:

```python
from __future__ import annotations
from typing import Protocol, runtime_checkable

@runtime_checkable
class DriftDetector(Protocol):
    """One-dimensional online drift detector.

    Implementations consume floats one at a time via `update`. `update` returns
    True when drift has just been detected (edge-triggered). `is_drifted`
    returns the latched state until the next reset.
    """
    name: str

    def update(self, value: float) -> bool: ...
    def is_drifted(self) -> bool: ...
    def value(self) -> float: ...
    def threshold(self) -> float: ...
    def reset(self) -> None: ...
```

- [ ] **Step 4: ADWIN**

`packages/agentaid-py/src/agentaid/drift/adwin.py`:

```python
from __future__ import annotations
import math
from collections import deque

class ADWIN:
    """Adaptive Windowing (Bifet & Gavaldà, 2007). One-dimensional change detector
    over a stream of bounded values in [0, 1]. Maintains a window of recent
    values and removes older sub-windows when their mean differs from the
    newer sub-window by more than the Hoeffding-derived bound.

    The implementation here keeps a single linear buffer for clarity; the
    original paper batches into compressed buckets for efficiency. For
    portfolio-scale streams (≤10^4 values) the linear version is adequate
    and easier to reason about.
    """
    name = "adwin"

    def __init__(self, delta: float = 0.002, max_window: int = 5000) -> None:
        self.delta = float(delta)
        self.max_window = int(max_window)
        self._window: deque[float] = deque()
        self._drifted = False
        self._last_value = 0.0
        self._last_threshold = 0.0

    def _bound(self, n0: int, n1: int) -> float:
        m = 1.0 / (1.0 / n0 + 1.0 / n1)
        return math.sqrt((1.0 / (2.0 * m)) * math.log(4.0 * (n0 + n1) / self.delta))

    def update(self, value: float) -> bool:
        v = float(value)
        self._last_value = v
        self._window.append(v)
        if len(self._window) > self.max_window:
            self._window.popleft()

        # Try splits and look for one that violates the Hoeffding bound.
        n = len(self._window)
        if n < 10:
            return False
        arr = list(self._window)
        cumsum = [0.0]
        for x in arr:
            cumsum.append(cumsum[-1] + x)

        for split in range(5, n - 5):
            n0, n1 = split, n - split
            mean0 = cumsum[split] / n0
            mean1 = (cumsum[n] - cumsum[split]) / n1
            eps = self._bound(n0, n1)
            self._last_threshold = eps
            if abs(mean0 - mean1) > eps:
                # Drop the older half (sub-window with stale mean).
                drop = split if mean0 < mean1 else 0
                if drop > 0:
                    for _ in range(drop):
                        self._window.popleft()
                self._drifted = True
                return True
        self._drifted = False
        return False

    def is_drifted(self) -> bool:
        return self._drifted

    def value(self) -> float:
        return self._last_value

    def threshold(self) -> float:
        return self._last_threshold

    def reset(self) -> None:
        self._window.clear()
        self._drifted = False
        self._last_value = 0.0
        self._last_threshold = 0.0
```

`packages/agentaid-py/src/agentaid/drift/__init__.py`:

```python
from .protocol import DriftDetector
from .adwin import ADWIN

__all__ = ["DriftDetector", "ADWIN"]
```

- [ ] **Step 5: Run tests, expect PASS**

```bash
uv run pytest packages/agentaid-py/tests/test_drift_adwin.py -v
```

If the second test fires too early or too late, tune `delta` (smaller = more conservative / fires later) and re-run. The acceptable window in the test is intentionally generous.

- [ ] **Step 6: Commit and close**

```bash
git add packages/agentaid-py
git commit -m "add drift detector protocol and adwin implementation"
bd close <id>
```

---

### Task 20: MMD and PSI detectors

**Goal:** Two more detectors for the remaining drift signals. MMD (Maximum Mean Discrepancy) for input embedding drift; PSI (Population Stability Index) for tool-call categorical-distribution drift.

**Files:**
- Create: `packages/agentaid-py/src/agentaid/drift/mmd.py`
- Create: `packages/agentaid-py/src/agentaid/drift/psi.py`
- Modify: `packages/agentaid-py/src/agentaid/drift/__init__.py`
- Test: `packages/agentaid-py/tests/test_drift_mmd_psi.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 20: mmd + psi drift detectors" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Failing test**

`packages/agentaid-py/tests/test_drift_mmd_psi.py`:

```python
import numpy as np
from agentaid.drift.mmd import MMDDetector
from agentaid.drift.psi import PSIDetector

def test_mmd_does_not_fire_on_same_distribution() -> None:
    rng = np.random.default_rng(0)
    ref = rng.normal(0, 1, size=(50, 8))
    mmd = MMDDetector(reference=ref, threshold=0.05, window=50)
    fired = False
    for _ in range(50):
        v = rng.normal(0, 1, size=8)
        if mmd.update(v):
            fired = True
    assert not fired

def test_mmd_fires_on_distribution_shift() -> None:
    rng = np.random.default_rng(1)
    ref = rng.normal(0, 1, size=(50, 8))
    mmd = MMDDetector(reference=ref, threshold=0.05, window=50)
    # Feed shifted samples
    fired = False
    for _ in range(80):
        v = rng.normal(2, 1, size=8)
        if mmd.update(v):
            fired = True
            break
    assert fired

def test_psi_zero_on_identical_distributions() -> None:
    psi = PSIDetector(reference={"a": 50, "b": 30, "c": 20}, threshold=0.1)
    for _ in range(50): psi.update("a")
    for _ in range(30): psi.update("b")
    for _ in range(20): psi.update("c")
    assert not psi.is_drifted()
    assert psi.value() < 0.05

def test_psi_fires_when_distribution_shifts() -> None:
    psi = PSIDetector(reference={"a": 50, "b": 30, "c": 20}, threshold=0.2)
    # Recent window heavily weights "c"
    for _ in range(10): psi.update("a")
    for _ in range(10): psi.update("b")
    for _ in range(80): psi.update("c")
    assert psi.is_drifted()
```

Run: `uv run pytest packages/agentaid-py/tests/test_drift_mmd_psi.py -v` → FAIL.

- [ ] **Step 3: Implement MMD**

`packages/agentaid-py/src/agentaid/drift/mmd.py`:

```python
from __future__ import annotations
from collections import deque
import numpy as np
from numpy.typing import NDArray

class MMDDetector:
    """Maximum Mean Discrepancy with an RBF kernel.

    Estimates MMD^2 between a fixed reference set and a sliding window of the
    most recent samples. Fires when MMD^2 exceeds `threshold`. The bandwidth
    `gamma` is set via the median heuristic at construction.
    """
    name = "mmd_rbf"

    def __init__(self, reference: NDArray[np.floating], *, threshold: float = 0.05,
                 window: int = 50, gamma: float | None = None) -> None:
        self.reference = np.asarray(reference, dtype=np.float64)
        self.threshold_value = float(threshold)
        self.window = int(window)
        self._buf: deque[NDArray[np.float64]] = deque(maxlen=window)
        self._drifted = False
        self._last_value = 0.0
        if gamma is None:
            gamma = self._median_heuristic(self.reference)
        self.gamma = float(gamma)

    @staticmethod
    def _median_heuristic(x: NDArray[np.float64]) -> float:
        if len(x) < 2:
            return 1.0
        n = min(len(x), 200)
        sub = x[:n]
        d = sub[:, None, :] - sub[None, :, :]
        sq = (d * d).sum(axis=-1)
        med = float(np.median(sq[sq > 0])) if (sq > 0).any() else 1.0
        return 1.0 / max(med, 1e-9)

    def _kernel_mean(self, a: NDArray[np.float64], b: NDArray[np.float64]) -> float:
        d = a[:, None, :] - b[None, :, :]
        sq = (d * d).sum(axis=-1)
        k = np.exp(-self.gamma * sq)
        return float(k.mean())

    def update(self, value: NDArray[np.floating]) -> bool:
        v = np.asarray(value, dtype=np.float64).reshape(-1)
        self._buf.append(v)
        if len(self._buf) < self.window:
            self._drifted = False
            return False
        cur = np.stack(list(self._buf), axis=0)
        mmd2 = (self._kernel_mean(self.reference, self.reference)
                + self._kernel_mean(cur, cur)
                - 2.0 * self._kernel_mean(self.reference, cur))
        self._last_value = float(max(0.0, mmd2))
        self._drifted = self._last_value > self.threshold_value
        return self._drifted

    def is_drifted(self) -> bool:
        return self._drifted

    def value(self) -> float:
        return self._last_value

    def threshold(self) -> float:
        return self.threshold_value

    def reset(self) -> None:
        self._buf.clear()
        self._drifted = False
        self._last_value = 0.0
```

- [ ] **Step 4: Implement PSI**

`packages/agentaid-py/src/agentaid/drift/psi.py`:

```python
from __future__ import annotations
import math
from collections import Counter, deque

class PSIDetector:
    """Population Stability Index over a sliding window of categorical values.

    PSI = sum_i (p_cur_i - p_ref_i) * ln(p_cur_i / p_ref_i)
    A value above ~0.1 traditionally signals minor shift; ~0.25 major.
    """
    name = "psi"

    def __init__(self, reference: dict[str, float], *, threshold: float = 0.2,
                 window: int = 100, smoothing: float = 1e-4) -> None:
        total = sum(reference.values())
        if total <= 0:
            raise ValueError("reference distribution must be non-empty")
        self._ref = {k: max(v / total, smoothing) for k, v in reference.items()}
        self.threshold_value = float(threshold)
        self.window_size = int(window)
        self.smoothing = smoothing
        self._buf: deque[str] = deque(maxlen=window)
        self._drifted = False
        self._last_value = 0.0

    def update(self, value: str) -> bool:
        self._buf.append(str(value))
        if len(self._buf) < max(20, self.window_size // 2):
            self._drifted = False
            return False
        counts = Counter(self._buf)
        total = sum(counts.values()) or 1
        psi = 0.0
        for k, ref_p in self._ref.items():
            cur_p = max(counts.get(k, 0) / total, self.smoothing)
            psi += (cur_p - ref_p) * math.log(cur_p / ref_p)
        # Account for new categories that weren't in reference.
        for k, c in counts.items():
            if k in self._ref:
                continue
            cur_p = max(c / total, self.smoothing)
            ref_p = self.smoothing
            psi += (cur_p - ref_p) * math.log(cur_p / ref_p)
        self._last_value = float(psi)
        self._drifted = self._last_value >= self.threshold_value
        return self._drifted

    def is_drifted(self) -> bool:
        return self._drifted

    def value(self) -> float:
        return self._last_value

    def threshold(self) -> float:
        return self.threshold_value

    def reset(self) -> None:
        self._buf.clear()
        self._drifted = False
        self._last_value = 0.0
```

- [ ] **Step 5: Update package init**

`packages/agentaid-py/src/agentaid/drift/__init__.py`:

```python
from .protocol import DriftDetector
from .adwin import ADWIN
from .mmd import MMDDetector
from .psi import PSIDetector

__all__ = ["DriftDetector", "ADWIN", "MMDDetector", "PSIDetector"]
```

- [ ] **Step 6: Run tests, expect PASS**

```bash
uv run pytest packages/agentaid-py/tests/test_drift_mmd_psi.py -v
```

- [ ] **Step 7: Commit and close**

```bash
git add packages/agentaid-py
git commit -m "add mmd and psi drift detectors"
bd close <id>
```

---

### Task 21: Server-side drift workers

**Goal:** Three worker functions on the server, one per signal. They poll new data (eval results, span attributes), feed the appropriate detector, persist state to `DriftStateRow`. A FastAPI startup hook spawns the workers; they run as a single async task each, on a 5-second tick.

**Files:**
- Create: `packages/agentaid-server/src/agentaid_server/orchestrator/drift_workers.py`
- Modify: `packages/agentaid-server/src/agentaid_server/main.py` (start workers in lifespan)
- Modify: `packages/agentaid-server/src/agentaid_server/api/drift.py` (add `/drift/series/{signal}` for charts)
- Test: `packages/agentaid-server/tests/test_drift_workers.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 21: server drift workers (3 signals)" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Failing test**

`packages/agentaid-server/tests/test_drift_workers.py`:

```python
import pytest
import asyncio
from datetime import datetime
from sqlmodel import select
from agentaid_server.db.engine import SessionLocal, init_db
from agentaid_server.db.models import EvalResult, DriftStateRow
from agentaid_server.orchestrator.drift_workers import quality_drift_tick

@pytest.mark.asyncio
async def test_quality_drift_tick_writes_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTAID_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'d.db'}")
    import importlib, agentaid_server.db.engine as eng
    importlib.reload(eng)
    await init_db()
    async with SessionLocal() as s:
        for i in range(60):
            score = 0.85 if i < 30 else 0.4   # mean shift downward
            s.add(EvalResult(run_id=f"r{i}", eval_name="relevance_judge",
                             mode="online", score=score,
                             created_at=datetime.utcnow()))
        await s.commit()

    await quality_drift_tick()
    async with SessionLocal() as s:
        rows = (await s.exec(select(DriftStateRow).where(DriftStateRow.signal == "quality"))).all()
    assert rows, "expected at least one quality drift state row"
    assert any(r.is_drifted for r in rows)
```

Run: `uv run pytest packages/agentaid-server/tests/test_drift_workers.py -v` → FAIL.

- [ ] **Step 3: Implement workers**

`packages/agentaid-server/src/agentaid_server/orchestrator/drift_workers.py`:

```python
from __future__ import annotations
import asyncio
import logging
import json
from datetime import datetime
import numpy as np
from sqlmodel import select
from agentaid.drift import ADWIN, MMDDetector, PSIDetector
from ..db.engine import SessionLocal
from ..db.models import EvalResult, Span, DriftStateRow

log = logging.getLogger(__name__)

# Module-level singletons; reset on import for tests.
_quality_detectors: dict[str, ADWIN] = {}
_tool_detectors: dict[str, PSIDetector] = {}
_input_detector: MMDDetector | None = None

# A static reference distribution for tool-call PSI is bootstrapped from the
# first batch of data (seeded by Task 22's seed_drift.py).
_TOOL_REFERENCE: dict[str, dict[str, float]] = {
    "planner": {"search_arxiv": 1.0, "fetch_metadata": 4.0,
                "score_candidate": 4.0, "compose_digest": 1.0,
                "dispatch_worker": 3.0},
    "worker":  {"fetch_paper": 3.0, "extract_figures": 3.0,
                "summarize": 3.0, "query_paper": 0.5},
}

async def quality_drift_tick() -> None:
    """ADWIN over recent eval scores per eval_name."""
    async with SessionLocal() as s:
        rows = (await s.exec(select(EvalResult).where(EvalResult.eval_name == "relevance_judge")
                              .order_by(EvalResult.created_at))).all()
    if not rows:
        return
    det = _quality_detectors.setdefault("relevance_judge", ADWIN(delta=0.002))
    last_drifted = False
    for r in rows:
        last_drifted = det.update(float(r.score)) or last_drifted

    async with SessionLocal() as s:
        s.add(DriftStateRow(
            signal="quality", detector_name="adwin",
            window=str(len(rows)), value=det.value(),
            threshold=det.threshold(),
            is_drifted=det.is_drifted() or last_drifted,
        ))
        await s.commit()

async def tool_call_drift_tick() -> None:
    """PSI per agent role over recent tool-call spans."""
    async with SessionLocal() as s:
        spans = (await s.exec(select(Span).where(Span.role.in_(["planner", "worker"]))
                              .order_by(Span.started_at.desc()).limit(500))).all()
    by_role: dict[str, list[str]] = {"planner": [], "worker": []}
    for sp in spans:
        # We expect tool-call spans to be named after the tool, parented under a role span.
        role = sp.role
        if role in by_role and sp.parent_span_id is not None:
            by_role[role].append(sp.name)
    state_rows: list[DriftStateRow] = []
    for role, calls in by_role.items():
        if not calls:
            continue
        det = _tool_detectors.setdefault(role,
            PSIDetector(reference=_TOOL_REFERENCE[role], threshold=0.2, window=200))
        for name in calls:
            det.update(name)
        state_rows.append(DriftStateRow(
            signal="tool_call", detector_name=f"psi:{role}",
            window=str(len(calls)), value=det.value(),
            threshold=det.threshold(), is_drifted=det.is_drifted(),
        ))
    if state_rows:
        async with SessionLocal() as s:
            for r in state_rows:
                s.add(r)
            await s.commit()

async def input_drift_tick() -> None:
    """MMD on user-input embeddings.

    Placeholder embedding: a hash-based vector of the research_interest string.
    Replaced with real embeddings (Anthropic or sentence-transformers) is a
    later optimization; the platform-shape signal is what matters for the
    portfolio. The detector still picks up topic drift via this proxy.
    """
    global _input_detector
    async with SessionLocal() as s:
        from .. db.models import Run as RunRow
        rows = (await s.exec(select(RunRow).order_by(RunRow.started_at).limit(1000))).all()
    if not rows:
        return

    def embed(s: str) -> np.ndarray:
        rng = np.random.default_rng(abs(hash(s)) % (2**32))
        return rng.normal(0, 1, size=8)

    interests = [(r.input or {}).get("research_interest", "") for r in rows]
    refs = np.stack([embed(x) for x in interests[:50]], axis=0) if len(interests) >= 50 else None
    if refs is None:
        return
    if _input_detector is None:
        _input_detector = MMDDetector(reference=refs, threshold=0.05, window=50)
    last_drifted = False
    for x in interests[50:]:
        last_drifted = _input_detector.update(embed(x)) or last_drifted

    async with SessionLocal() as s2:
        s2.add(DriftStateRow(
            signal="input", detector_name="mmd_rbf",
            window=str(len(interests)),
            value=_input_detector.value(),
            threshold=_input_detector.threshold(),
            is_drifted=_input_detector.is_drifted() or last_drifted,
        ))
        await s2.commit()

async def drift_loop(interval_s: float = 5.0) -> None:
    while True:
        try:
            await asyncio.gather(quality_drift_tick(), tool_call_drift_tick(), input_drift_tick())
        except Exception:
            log.exception("drift tick failed")
        await asyncio.sleep(interval_s)
```

- [ ] **Step 4: Wire into lifespan**

In `main.py`:

```python
import asyncio
from .orchestrator.drift_workers import drift_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(drift_loop())
    try:
        yield
    finally:
        task.cancel()
```

- [ ] **Step 5: Add drift series endpoint**

In `packages/agentaid-server/src/agentaid_server/api/drift.py`:

```python
@router.get("/drift/series/{signal}")
async def drift_series(signal: str, limit: int = 200) -> dict:
    async with SessionLocal() as s:
        rows = (await s.exec(select(DriftStateRow)
                              .where(DriftStateRow.signal == signal)
                              .order_by(DriftStateRow.updated_at.desc())
                              .limit(limit))).all()
    return {"points": [r.model_dump() for r in reversed(rows)]}
```

- [ ] **Step 6: Run tests, expect PASS**

```bash
uv run pytest packages/agentaid-server/tests/test_drift_workers.py -v
```

- [ ] **Step 7: Commit and close**

```bash
git add packages/agentaid-server
git commit -m "add drift workers for quality, tool-call, and input signals"
bd close <id>
```

---

### Task 22: Synthetic drift seed script

**Goal:** `scripts/seed_drift.py` produces synthetic data designed to deliberately trigger each detector. Used for the demo so drift visibly fires; also exercised by integration tests.

**Files:**
- Create: `scripts/seed_drift.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 22: synthetic drift seed script" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Implement seed script**

`scripts/seed_drift.py`:

```python
"""Seed AgentAid with synthetic data designed to fire each drift detector.

Usage:
    uv run python scripts/seed_drift.py [--db sqlite+aiosqlite:///./agentaid.db]

Produces:
- 100 synthetic runs across two epochs (0..49 stable, 50..99 shifted) per signal
- 60 quality eval results: 30 high (~0.85), then 30 low (~0.40)
- 200 tool-call spans: first half follows the reference distribution, second
  half over-uses extract_figures (drives PSI > 0.2 on worker)
- 100 runs with research_interest values drawn from one topic for the first
  half and a different topic for the second half (drives MMD).

After running, re-tick the drift workers (or wait 5s for the live loop).
"""
from __future__ import annotations
import argparse
import asyncio
import os
import random
from datetime import datetime, timedelta
from agentaid_server.db.engine import init_db, SessionLocal
from agentaid_server.db.models import Run, Span, EvalResult

EPOCHS = [
    {"interest": "concept drift in streaming ML", "tools": ["fetch_paper", "extract_figures", "summarize"]},
    {"interest": "transformer alignment in robotics", "tools": ["fetch_paper", "extract_figures", "extract_figures", "extract_figures", "summarize"]},
]

async def seed(db_url: str | None) -> None:
    if db_url:
        os.environ["AGENTAID_DB_URL"] = db_url
        import importlib, agentaid_server.db.engine as eng
        importlib.reload(eng)
    await init_db()

    base = datetime.utcnow() - timedelta(days=2)
    async with SessionLocal() as s:
        for i in range(100):
            epoch = EPOCHS[0] if i < 50 else EPOCHS[1]
            run_id = f"seed-{i:04d}"
            run_started = base + timedelta(minutes=i * 5)
            run_ended = run_started + timedelta(seconds=12)
            s.add(Run(id=run_id, agent_name="arxiv-planner",
                      started_at=run_started, ended_at=run_ended, status="succeeded",
                      total_cost=0.02 + random.uniform(0, 0.005),
                      total_tokens=2000 + random.randint(0, 500),
                      input={"research_interest": epoch["interest"]},
                      output={"digest": "## P\n- summary\n2401.00001"}))
            # Planner span
            s.add(Span(id=f"{run_id}-p", run_id=run_id, parent_span_id=None,
                       name="planner", role="planner",
                       started_at=run_started, ended_at=run_ended, attributes={}, events=[]))
            # Worker child spans (one per tool call in the epoch)
            for j, tool in enumerate(epoch["tools"]):
                start = run_started + timedelta(seconds=1 + j)
                s.add(Span(id=f"{run_id}-t{j}", run_id=run_id, parent_span_id=f"{run_id}-p",
                           name=tool, role="worker",
                           started_at=start, ended_at=start + timedelta(seconds=1),
                           attributes={"agentaid.role": "worker"}, events=[]))
            # Eval results: first half high, second half low (shift in middle)
            score = random.gauss(0.85, 0.04) if i < 50 else random.gauss(0.40, 0.05)
            s.add(EvalResult(run_id=run_id, eval_name="relevance_judge",
                             mode="online", score=max(0.0, min(1.0, score)),
                             label="judged",
                             rationale="seeded",
                             created_at=run_ended))
        await s.commit()
    print(f"Seeded 100 runs, ~500 spans, 100 eval results to {os.getenv('AGENTAID_DB_URL', 'default')}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=None)
    args = p.parse_args()
    asyncio.run(seed(args.db))
```

- [ ] **Step 3: Run the seed and verify drift fires**

```bash
uv run python scripts/seed_drift.py
# Wait for at least one drift loop tick (default 5s), then:
curl -s http://localhost:8000/drift | python -m json.tool
```

Expected: at least one signal with `is_drifted: true`.

- [ ] **Step 4: Commit and close**

```bash
git add scripts
git commit -m "add synthetic drift seed script"
bd close <id>
```

---

### Task 23: Drift home goes live + Drift detail × 3

**Goal:** Drift home page now consumes real data from `/drift`. Add `DriftDetail` route at `/drift/:signal` showing time series + recent contributing runs.

**Files:**
- Modify: `packages/agentaid-web/src/api/client.ts` (`driftSeries` method)
- Modify: `packages/agentaid-web/src/routes/DriftDetail.tsx`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 23: drift home live + drift detail x3" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Add client method**

In `client.ts`:

```typescript
  driftSeries: (signal: "input" | "tool_call" | "quality"): Promise<{ points: DriftState[] }> =>
    getJson(`/drift/series/${signal}`),
```

- [ ] **Step 3: Implement DriftDetail**

`packages/agentaid-web/src/routes/DriftDetail.tsx`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, ReferenceLine } from "recharts";
import { api } from "../api/client";
import type { DriftSignal } from "../api/types";

const TITLES: Record<DriftSignal, string> = {
  input: "Input drift (MMD on query embeddings)",
  tool_call: "Tool-call distribution drift (PSI per role)",
  quality: "Quality drift (ADWIN on relevance_judge)",
};

export default function DriftDetail() {
  const { signal = "input" } = useParams();
  const sig = signal as DriftSignal;
  const series = useQuery({ queryKey: ["drift-series", sig], queryFn: () => api.driftSeries(sig), refetchInterval: 5000 });

  const points = (series.data?.points ?? []).map((p, i) => ({
    idx: i, value: p.value, threshold: p.threshold, drifted: p.is_drifted ? 1 : 0,
  }));
  const last = points[points.length - 1];

  return (
    <div>
      <Link to="/" style={{ fontSize: 12 }}>← back to monitoring</Link>
      <h2>{TITLES[sig] ?? "Drift detail"}</h2>
      <div style={{ marginTop: 8, fontSize: 13 }}>
        Latest: {last ? <><strong>{last.value.toFixed(4)}</strong> (threshold {last.threshold.toFixed(4)}) — {last.drifted ? "▲ drifted" : "stable"}</> : "no data"}
      </div>
      <div style={{ height: 240, marginTop: 16 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points}>
            <XAxis dataKey="idx" hide />
            <YAxis />
            <Tooltip />
            <Line dataKey="value" dot={false} stroke="#4a90e2" />
            {last && <ReferenceLine y={last.threshold} stroke="#c0392b" strokeDasharray="3 3" />}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

(The Drift home page already polls `/drift` so it goes live automatically once the workers are running.)

- [ ] **Step 4: Smoke**

Run server, run seed script, open `/` and `/drift/quality`. Expected: signal cards reflect real values; the chart on `/drift/quality` plateaus then drops below the threshold around index 60 (where the synthetic shift was applied).

- [ ] **Step 5: Commit and close**

```bash
git add packages/agentaid-web
git commit -m "implement drift detail pages and wire home to live data"
bd close <id>
```

---

## Phase 7 — Run Comparison + Mode 2 Regression (Day 7 part 1, ~6h)

### Task 24: Mode 2 regression suite (server + datasets API)

**Goal:** Implement the offline regression mode end-to-end. `POST /regressions` triggers a regression run against a dataset; the server runs the agent for each row, ingests the resulting traces, runs reference-based scoring, aggregates results into `RegressionRun.summary`. Plus dataset CRUD endpoints to seed `eval/golden/dataset.json` into the database.

**Files:**
- Create: `packages/agentaid-server/src/agentaid_server/orchestrator/regression.py`
- Create: `packages/agentaid-server/src/agentaid_server/api/regression.py`
- Create: `packages/agentaid-server/src/agentaid_server/api/datasets.py`
- Modify: `packages/agentaid-server/src/agentaid_server/main.py`
- Create: `scripts/load_golden.py`
- Test: `packages/agentaid-server/tests/test_regression.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 24: mode 2 regression suite end to end" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Failing test**

`packages/agentaid-server/tests/test_regression.py`:

```python
import pytest
from datetime import datetime
from sqlmodel import select
from agentaid_server.db.engine import SessionLocal, init_db
from agentaid_server.db.models import Dataset, DatasetRow, RegressionRun
from agentaid_server.orchestrator.regression import score_against_expected

def test_score_against_expected_rewards_overlap() -> None:
    expected = {"expected_paper_ids": ["2401.00001", "2402.00012"],
                "expected_themes": ["concept drift", "Hoeffding bound"]}
    actual_digest = "## 2401.00001\nNotes about concept drift and Hoeffding bound."
    actual_papers = ["2401.00001"]
    s = score_against_expected(expected, actual_digest, actual_papers)
    assert 0.0 <= s.recall_paper_ids <= 1.0
    assert 0.0 <= s.theme_coverage <= 1.0
    assert s.recall_paper_ids == 0.5

def test_score_against_expected_zero_when_no_overlap() -> None:
    s = score_against_expected({"expected_paper_ids": ["x"], "expected_themes": ["y"]},
                               "completely off-topic", [])
    assert s.recall_paper_ids == 0.0
    assert s.theme_coverage == 0.0
```

Run: `uv run pytest packages/agentaid-server/tests/test_regression.py -v` → FAIL.

- [ ] **Step 3: Reference-based scoring + driver**

`packages/agentaid-server/src/agentaid_server/orchestrator/regression.py`:

```python
from __future__ import annotations
import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from sqlmodel import select
from ..db.engine import SessionLocal
from ..db.models import Dataset, DatasetRow, RegressionRun, Run

log = logging.getLogger(__name__)

@dataclass(frozen=True)
class RowScore:
    row_id: str
    recall_paper_ids: float
    theme_coverage: float

def score_against_expected(expected: dict,
                            digest_text: str,
                            actual_paper_ids: list[str]) -> RowScore:
    expected_ids = set(expected.get("expected_paper_ids", []))
    actual_ids = set(actual_paper_ids)
    recall = (len(expected_ids & actual_ids) / len(expected_ids)) if expected_ids else 1.0

    themes = expected.get("expected_themes", [])
    digest_low = (digest_text or "").lower()
    hits = sum(1 for t in themes if t.lower() in digest_low)
    coverage = (hits / len(themes)) if themes else 1.0

    return RowScore(row_id=expected.get("id", ""),
                    recall_paper_ids=recall,
                    theme_coverage=coverage)

async def run_regression(dataset_id: str, prompt_sha: str, model: str) -> str:
    """Drive the agent across a dataset and aggregate results.

    Imports the agent lazily to keep the server side independent of pydantic_ai
    when only ingesting external traces.
    """
    from arxiv_agent.planner import build_planner_agent, PlannerInput

    rid = f"reg-{uuid.uuid4().hex[:12]}"
    started = datetime.utcnow()

    async with SessionLocal() as s:
        dataset = (await s.exec(select(Dataset).where(Dataset.id == dataset_id))).first()
        rows = (await s.exec(select(DatasetRow).where(DatasetRow.dataset_id == dataset_id))).all()
        s.add(RegressionRun(id=rid, dataset_id=dataset_id,
                            prompt_sha=prompt_sha, model=model,
                            started_at=started, status="running",
                            summary={"row_count": len(rows)}))
        await s.commit()

    if not rows:
        return rid

    agent = build_planner_agent()
    scores: list[RowScore] = []
    for row in rows:
        try:
            result = await agent.run(PlannerInput(
                research_interest=row.input["research_interest"],
                date_from=row.input["date_from"],
                date_to=row.input["date_to"],
            ))
            actual_ids = [c.paper_id for c in result.output.candidates[:3]]
            row_expected = dict(row.expected)
            row_expected["id"] = row.id
            scores.append(score_against_expected(row_expected, result.output.digest, actual_ids))
        except Exception:
            log.exception("regression row %s failed", row.id)
            scores.append(RowScore(row_id=row.id, recall_paper_ids=0.0, theme_coverage=0.0))

    summary = {
        "row_count": len(rows),
        "mean_recall": sum(s.recall_paper_ids for s in scores) / len(scores),
        "mean_theme_coverage": sum(s.theme_coverage for s in scores) / len(scores),
        "per_row": [s.__dict__ for s in scores],
    }
    async with SessionLocal() as s:
        rec = (await s.exec(select(RegressionRun).where(RegressionRun.id == rid))).first()
        if rec is not None:
            rec.ended_at = datetime.utcnow()
            rec.status = "succeeded"
            rec.summary = summary
            s.add(rec)
            await s.commit()
    return rid
```

- [ ] **Step 4: API surfaces**

`packages/agentaid-server/src/agentaid_server/api/datasets.py`:

```python
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from sqlmodel import select
from ..db.engine import SessionLocal
from ..db.models import Dataset, DatasetRow

router = APIRouter()

@router.get("/datasets")
async def list_datasets() -> dict:
    async with SessionLocal() as s:
        ds = (await s.exec(select(Dataset))).all()
    return {"datasets": [d.model_dump() for d in ds]}

@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str) -> dict:
    async with SessionLocal() as s:
        d = (await s.exec(select(Dataset).where(Dataset.id == dataset_id))).first()
        if d is None:
            raise HTTPException(404, f"dataset {dataset_id} not found")
        rows = (await s.exec(select(DatasetRow).where(DatasetRow.dataset_id == dataset_id))).all()
    return {"dataset": d.model_dump(), "rows": [r.model_dump() for r in rows]}
```

`packages/agentaid-server/src/agentaid_server/api/regression.py`:

```python
from __future__ import annotations
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import select
from ..db.engine import SessionLocal
from ..db.models import RegressionRun
from ..orchestrator.regression import run_regression

router = APIRouter()

class RegressionRequest(BaseModel):
    dataset_id: str
    prompt_sha: str
    model: str = "claude-sonnet-4-6"

@router.post("/regressions")
async def trigger_regression(req: RegressionRequest, bg: BackgroundTasks) -> dict[str, str]:
    bg.add_task(run_regression, req.dataset_id, req.prompt_sha, req.model)
    return {"status": "scheduled"}

@router.get("/regressions/{run_id}")
async def get_regression(run_id: str) -> dict:
    async with SessionLocal() as s:
        r = (await s.exec(select(RegressionRun).where(RegressionRun.id == run_id))).first()
    return {"regression": r.model_dump() if r else None}

@router.get("/regressions")
async def list_regressions(limit: int = 20) -> dict:
    async with SessionLocal() as s:
        rows = (await s.exec(select(RegressionRun).order_by(RegressionRun.started_at.desc()).limit(limit))).all()
    return {"regressions": [r.model_dump() for r in rows]}
```

Mount both in `main.py`:

```python
from .api import datasets as datasets_api, regression as regression_api
app.include_router(datasets_api.router)
app.include_router(regression_api.router)
```

- [ ] **Step 5: Loader script for the golden dataset**

`scripts/load_golden.py`:

```python
"""Load eval/golden/dataset.json into the AgentAid database as a Dataset + DatasetRows."""
from __future__ import annotations
import asyncio
import json
import uuid
from pathlib import Path
from agentaid_server.db.engine import init_db, SessionLocal
from agentaid_server.db.models import Dataset, DatasetRow

GOLDEN = Path(__file__).resolve().parent.parent / "eval" / "golden" / "dataset.json"

async def main() -> None:
    await init_db()
    data = json.loads(GOLDEN.read_text())
    ds_id = "golden-arxiv-v1"
    async with SessionLocal() as s:
        s.add(Dataset(id=ds_id, name=data["name"], description=data.get("description")))
        for row in data["rows"]:
            s.add(DatasetRow(id=row["id"], dataset_id=ds_id,
                             input=row["input"], expected=row["expected"]))
        await s.commit()
    print(f"loaded {len(data['rows'])} rows into dataset {ds_id}")

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 6: Run tests, expect PASS**

```bash
uv run pytest packages/agentaid-server/tests/test_regression.py -v
```

- [ ] **Step 7: Manual smoke**

```bash
uv run python scripts/load_golden.py
curl -s -X POST http://localhost:8000/regressions \
  -H 'content-type: application/json' \
  -d '{"dataset_id":"golden-arxiv-v1","prompt_sha":"HEAD","model":"claude-sonnet-4-6"}'
sleep 30   # let the agent chew through the rows
curl -s http://localhost:8000/regressions | python -m json.tool | head -50
```

Expected: regression runs eventually report `status: succeeded` with `summary.mean_recall` and `summary.mean_theme_coverage` populated.

- [ ] **Step 8: Commit and close**

```bash
git add packages/agentaid-server scripts
git commit -m "implement mode 2 regression suite end-to-end"
bd close <id>
```

---

### Task 25: Run comparison view (frontend)

**Goal:** Implement `/compare?a=:id&b=:id` with the summary-led layout from the spec — scorecard, tool-call distribution shift, drift contribution callout, expandable Gantt overlay / output diff.

**Files:**
- Modify: `packages/agentaid-web/src/api/client.ts` (`compareRuns` method)
- Modify: `packages/agentaid-web/src/routes/RunComparison.tsx`
- Create: `packages/agentaid-web/src/components/ScoreCard.tsx`
- Create: `packages/agentaid-server/src/agentaid_server/api/compare.py`
- Modify: `packages/agentaid-server/src/agentaid_server/main.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 25: run comparison view + compare api" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Server-side compare endpoint**

`packages/agentaid-server/src/agentaid_server/api/compare.py`:

```python
from __future__ import annotations
from collections import Counter
from fastapi import APIRouter, HTTPException
from sqlmodel import select
from ..db.engine import SessionLocal
from ..db.models import Run, Span, EvalResult

router = APIRouter()

@router.get("/compare")
async def compare(a: str, b: str) -> dict:
    async with SessionLocal() as s:
        run_a = (await s.exec(select(Run).where(Run.id == a))).first()
        run_b = (await s.exec(select(Run).where(Run.id == b))).first()
        if not run_a or not run_b:
            raise HTTPException(404, "one or both runs not found")
        spans_a = (await s.exec(select(Span).where(Span.run_id == a))).all()
        spans_b = (await s.exec(select(Span).where(Span.run_id == b))).all()
        evals_a = (await s.exec(select(EvalResult).where(EvalResult.run_id == a))).all()
        evals_b = (await s.exec(select(EvalResult).where(EvalResult.run_id == b))).all()

    def _tool_dist(spans: list[Span]) -> Counter:
        return Counter(sp.name for sp in spans if sp.parent_span_id is not None)

    dist_a, dist_b = _tool_dist(spans_a), _tool_dist(spans_b)
    all_tools = sorted(set(dist_a) | set(dist_b))

    scores = {}
    for r in evals_a:
        scores.setdefault(r.eval_name, {})["a"] = r.score
    for r in evals_b:
        scores.setdefault(r.eval_name, {})["b"] = r.score

    return {
        "a": run_a.model_dump(),
        "b": run_b.model_dump(),
        "tool_distribution": [
            {"tool": t, "a_count": dist_a.get(t, 0), "b_count": dist_b.get(t, 0)}
            for t in all_tools
        ],
        "scores": [{"eval_name": k, **v} for k, v in scores.items()],
    }
```

Mount in `main.py`:

```python
from .api import compare as compare_api
app.include_router(compare_api.router)
```

- [ ] **Step 3: Client method + types**

In `client.ts`:

```typescript
  compareRuns: (a: string, b: string): Promise<CompareResult> =>
    getJson<CompareResult>(`/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`),
```

In `types.ts`, append:

```typescript
export interface CompareResult {
  a: Run;
  b: Run;
  tool_distribution: Array<{ tool: string; a_count: number; b_count: number }>;
  scores: Array<{ eval_name: string; a?: number; b?: number }>;
}
```

- [ ] **Step 4: ScoreCard component**

`packages/agentaid-web/src/components/ScoreCard.tsx`:

```typescript
interface Props {
  label: string;
  a: number | null | undefined;
  b: number | null | undefined;
  format?: (v: number) => string;
}
export default function ScoreCard({ label, a, b, format = (v) => v.toFixed(3) }: Props) {
  const have = a !== undefined && a !== null && b !== undefined && b !== null;
  const delta = have ? (b! - a!) : null;
  const pct = have && a !== 0 ? ((b! - a!) / Math.abs(a!)) * 100 : null;
  const color = delta === null ? "inherit" : delta > 0 ? "#27ae60" : delta < 0 ? "#c0392b" : "inherit";
  return (
    <div style={{ padding: 12, border: "1px solid #eee", textAlign: "left" }}>
      <div style={{ fontSize: 10, opacity: 0.75, textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 16, marginTop: 4 }}>
        <strong>{a !== null && a !== undefined ? format(a!) : "—"} → {b !== null && b !== undefined ? format(b!) : "—"}</strong>
      </div>
      <div style={{ color, fontSize: 12 }}>
        {delta === null ? "—"
          : `${delta > 0 ? "▲" : delta < 0 ? "▼" : "·"} ${format(Math.abs(delta))}${pct !== null ? ` (${pct.toFixed(0)}%)` : ""}`}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Implement RunComparison route**

`packages/agentaid-web/src/routes/RunComparison.tsx`:

```typescript
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import ScoreCard from "../components/ScoreCard";

export default function RunComparison() {
  const [params] = useSearchParams();
  const a = params.get("a") ?? "";
  const b = params.get("b") ?? "";
  const cmp = useQuery({ queryKey: ["compare", a, b], queryFn: () => api.compareRuns(a, b),
                         enabled: Boolean(a && b) });
  if (!a || !b) return <div>Provide ?a=&lt;run-id&gt;&amp;b=&lt;run-id&gt;.</div>;
  if (cmp.isLoading || !cmp.data) return <div>Loading…</div>;
  const { a: ra, b: rb, tool_distribution, scores } = cmp.data;
  const findScore = (n: string) => scores.find(s => s.eval_name === n);
  const rel = findScore("relevance_judge");
  const fa = findScore("faithfulness_judge");

  return (
    <div>
      <div style={{ fontSize: 13, marginBottom: 8 }}>
        <strong>{ra.id}</strong> &nbsp;vs&nbsp; <strong>{rb.id}</strong>
        &nbsp;<span style={{ opacity: 0.6 }}>(prompt {ra.prompt_sha ?? "—"} → {rb.prompt_sha ?? "—"})</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginBottom: 18 }}>
        <ScoreCard label="Relevance" a={rel?.a} b={rel?.b} />
        <ScoreCard label="Faithfulness" a={fa?.a} b={fa?.b} />
        <ScoreCard label="Cost" a={ra.total_cost} b={rb.total_cost} format={(v) => `$${v.toFixed(4)}`} />
        <ScoreCard label="Tokens" a={ra.total_tokens} b={rb.total_tokens} format={(v) => `${Math.round(v)}`} />
      </div>

      <div style={{ fontSize: 11, opacity: 0.75, textTransform: "uppercase", marginTop: 12 }}>
        Tool-call distribution shift
      </div>
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${tool_distribution.length}, 1fr)`, gap: 6, marginTop: 6 }}>
        {tool_distribution.map((t) => {
          const delta = t.b_count - t.a_count;
          return (
            <div key={t.tool} style={{ padding: 8, border: "1px solid #eee", textAlign: "center" }}>
              <div style={{ fontSize: 10, opacity: 0.7 }}>{t.tool}</div>
              <div style={{ fontSize: 11, marginTop: 4 }}>
                {t.a_count} → {t.b_count} <span style={{ color: delta > 0 ? "#c0392b" : delta < 0 ? "#27ae60" : "inherit" }}>
                  {delta === 0 ? "·" : delta > 0 ? `+${delta}` : delta}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Smoke**

```bash
pnpm --filter agentaid-web typecheck
pnpm --filter agentaid-web dev
```

Pick two run IDs from `/runs`; navigate to `/compare?a=<id1>&b=<id2>`. Verify scorecards and tool distribution render.

- [ ] **Step 7: Commit and close**

```bash
git add packages/agentaid-web packages/agentaid-server
git commit -m "implement run comparison view and compare api"
bd close <id>
```

---

### Task 26: Datasets and Run List pages

**Goal:** Two remaining frontend routes — `Datasets` (list datasets, view rows, trigger a regression) and `RunList` (search/filter runs by status / agent / score).

**Files:**
- Modify: `packages/agentaid-web/src/api/client.ts` (datasets, regressions)
- Modify: `packages/agentaid-web/src/routes/Datasets.tsx`
- Modify: `packages/agentaid-web/src/routes/RunList.tsx`
- Modify: `packages/agentaid-web/src/api/types.ts`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 26: datasets + run list pages" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Add types**

In `types.ts`:

```typescript
export interface DatasetSummary { id: string; name: string; description: string | null }
export interface DatasetRow { id: string; dataset_id: string; input: Record<string, unknown>; expected: Record<string, unknown> }
export interface DatasetDetail { dataset: DatasetSummary; rows: DatasetRow[] }
export interface RegressionSummary {
  id: string; dataset_id: string; prompt_sha: string | null; model: string | null;
  started_at: string; ended_at: string | null; status: string;
  summary: Record<string, unknown>;
}
```

- [ ] **Step 3: Add client methods**

In `client.ts`:

```typescript
  listDatasets: (): Promise<{ datasets: DatasetSummary[] }> => getJson(`/datasets`),
  getDataset: (id: string): Promise<DatasetDetail> => getJson(`/datasets/${id}`),
  listRegressions: (): Promise<{ regressions: RegressionSummary[] }> => getJson(`/regressions`),
  triggerRegression: async (req: { dataset_id: string; prompt_sha: string; model?: string }) => {
    const res = await fetch(`${BASE}/regressions`, {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  },
```

- [ ] **Step 4: Implement Datasets page**

`packages/agentaid-web/src/routes/Datasets.tsx`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";

export default function Datasets() {
  const qc = useQueryClient();
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: () => api.listDatasets() });
  const regressions = useQuery({ queryKey: ["regressions"], queryFn: () => api.listRegressions(), refetchInterval: 5000 });
  const [selected, setSelected] = useState<string | null>(null);
  const detail = useQuery({ queryKey: ["dataset", selected], queryFn: () => api.getDataset(selected!), enabled: Boolean(selected) });
  const trigger = useMutation({
    mutationFn: (datasetId: string) => api.triggerRegression({ dataset_id: datasetId, prompt_sha: "HEAD" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["regressions"] }),
  });

  return (
    <div>
      <h2>Datasets</h2>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 16 }}>
        <div>
          {(datasets.data?.datasets ?? []).map((d) => (
            <button key={d.id} onClick={() => setSelected(d.id)}
              style={{ display: "block", padding: 8, marginBottom: 6, width: "100%",
                       textAlign: "left", border: selected === d.id ? "2px solid #4a90e2" : "1px solid #eee",
                       background: "white", cursor: "pointer" }}>
              <strong>{d.name}</strong>
              <div style={{ fontSize: 11, opacity: 0.7 }}>{d.description}</div>
            </button>
          ))}
        </div>
        <div>
          {detail.data && (
            <>
              <div style={{ marginBottom: 8 }}>
                <strong>{detail.data.dataset.name}</strong> — {detail.data.rows.length} rows
                <button onClick={() => trigger.mutate(detail.data!.dataset.id)}
                  style={{ marginLeft: 12, padding: "4px 8px", border: "1px solid #4a90e2",
                           background: "white", cursor: "pointer" }}>
                  Run regression
                </button>
              </div>
              <pre style={{ background: "#f7f7f7", padding: 8, fontSize: 11, maxHeight: 200, overflow: "auto" }}>
                {JSON.stringify(detail.data.rows.slice(0, 3), null, 2)}
              </pre>
            </>
          )}
          <h3 style={{ marginTop: 24 }}>Recent regression runs</h3>
          {(regressions.data?.regressions ?? []).map((r) => (
            <div key={r.id} style={{ fontSize: 11, fontFamily: "ui-monospace, monospace",
                                      padding: 6, borderBottom: "1px solid #eee" }}>
              {r.id} · {r.dataset_id} · {r.status}
              &nbsp;·&nbsp; mean_recall={(r.summary as Record<string, number>)?.mean_recall?.toFixed(3) ?? "—"}
              &nbsp;·&nbsp; mean_theme={(r.summary as Record<string, number>)?.mean_theme_coverage?.toFixed(3) ?? "—"}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Implement RunList page**

`packages/agentaid-web/src/routes/RunList.tsx`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import RunRow from "../components/RunRow";

export default function RunList() {
  const [filter, setFilter] = useState("");
  const runs = useQuery({ queryKey: ["runs", { limit: 200 }], queryFn: () => api.listRuns({ limit: 200 }), refetchInterval: 10_000 });
  const filtered = (runs.data?.runs ?? []).filter((r) =>
    !filter ||
    r.id.includes(filter) ||
    r.agent_name.includes(filter) ||
    (r.input ? JSON.stringify(r.input).toLowerCase().includes(filter.toLowerCase()) : false));
  return (
    <div>
      <h2>Traces</h2>
      <input value={filter} onChange={(e) => setFilter(e.target.value)}
        placeholder="search runs (id, agent, input)…"
        style={{ width: "100%", padding: 8, border: "1px solid #ddd", marginBottom: 12 }} />
      {filtered.map((r) => <RunRow key={r.id} run={r} />)}
      {filtered.length === 0 && <div style={{ opacity: 0.6 }}>No runs match.</div>}
    </div>
  );
}
```

- [ ] **Step 6: Smoke + commit**

```bash
pnpm --filter agentaid-web typecheck
pnpm --filter agentaid-web dev
```

Verify `/datasets` loads and the "Run regression" button enqueues a run; `/runs` filters as you type.

```bash
git add packages/agentaid-web
git commit -m "implement datasets and run list pages"
bd close <id>
```

---

## Phase 8 — TypeScript SDK (Day 7 part 2, ~7h)

### Task 27: agentaid-ts SDK (otel exporter, eval define, invariants)

**Goal:** A TypeScript SDK that mirrors the Python SDK's surface for instrumentation and eval definition. No drift detectors — those run server-side. Demonstrates Python/TS parity in the platform's contract.

**Files:**
- Create: `packages/agentaid-ts/src/index.ts`
- Create: `packages/agentaid-ts/src/otel/conventions.ts`
- Create: `packages/agentaid-ts/src/otel/exporter.ts`
- Create: `packages/agentaid-ts/src/eval/models.ts`
- Create: `packages/agentaid-ts/src/eval/define.ts`
- Create: `packages/agentaid-ts/src/eval/invariants.ts`
- Create: `packages/agentaid-ts/tsconfig.json`
- Create: `packages/agentaid-ts/src/index.test.ts`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 27: typescript sdk parity (otel + eval define + invariants)" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: tsconfig**

`packages/agentaid-ts/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "declaration": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "types": ["vitest/globals"]
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Failing tests**

`packages/agentaid-ts/src/index.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { defineEval, EvalMode, type Run } from "./eval/define";
import { listEvals, getEval, _resetForTests } from "./eval/define";
import { runInvariants } from "./eval/invariants";

beforeEach(() => _resetForTests());

describe("defineEval", () => {
  it("registers an eval and lists it", () => {
    defineEval({
      name: "x_inv",
      mode: EvalMode.Invariant,
      fn: async (run: Run) => ({ runId: run.id, evalName: "x_inv", mode: EvalMode.Invariant, score: 1 }),
    });
    expect(listEvals()).toContain("x_inv");
    expect(getEval("x_inv").mode).toBe(EvalMode.Invariant);
  });

  it("throws on duplicate registration", () => {
    defineEval({ name: "dup", mode: EvalMode.Invariant, fn: async (r) => ({ runId: r.id, evalName: "dup", mode: EvalMode.Invariant, score: 0 }) });
    expect(() => defineEval({ name: "dup", mode: EvalMode.Invariant, fn: async (r) => ({ runId: r.id, evalName: "dup", mode: EvalMode.Invariant, score: 0 }) })).toThrow();
  });
});

describe("runInvariants", () => {
  it("dispatches all invariant evals against a run", async () => {
    const fn = vi.fn(async (run: Run) => ({ runId: run.id, evalName: "ok", mode: EvalMode.Invariant, score: 1 }));
    defineEval({ name: "ok", mode: EvalMode.Invariant, fn });
    const results = await runInvariants({ id: "r1", agentName: "a", startedAt: new Date().toISOString(), input: null, output: null });
    expect(results).toHaveLength(1);
    expect(results[0].score).toBe(1);
    expect(fn).toHaveBeenCalled();
  });
});
```

Run: `pnpm --filter agentaid add -D vitest && pnpm --filter agentaid test` → FAIL.

- [ ] **Step 4: Conventions**

`packages/agentaid-ts/src/otel/conventions.ts`:

```typescript
export const GenAI = {
  System: "gen_ai.system",
  RequestModel: "gen_ai.request.model",
  ResponseModel: "gen_ai.response.model",
  UsageInputTokens: "gen_ai.usage.input_tokens",
  UsageOutputTokens: "gen_ai.usage.output_tokens",
  OperationName: "gen_ai.operation.name",
  ToolName: "gen_ai.tool.name",
  ToolCallId: "gen_ai.tool.call.id",
} as const;

export const AgentAid = {
  RunId: "agentaid.run_id",
  Role: "agentaid.role",
  PromptSha: "agentaid.prompt_sha",
  AgentName: "agentaid.agent_name",
  EvalResult: "agentaid.eval_result",
  Input: "agentaid.input",
  Output: "agentaid.output",
} as const;
```

- [ ] **Step 5: Exporter**

`packages/agentaid-ts/src/otel/exporter.ts`:

```typescript
import { ExportResult, ExportResultCode } from "@opentelemetry/core";
import type { ReadableSpan, SpanExporter } from "@opentelemetry/sdk-trace-base";

interface SerializedSpan {
  trace_id: string;
  span_id: string;
  parent_span_id: string | null;
  name: string;
  kind: string;
  start_time_unix_nano: number;
  end_time_unix_nano: number;
  attributes: Record<string, unknown>;
  events: Array<{ name: string; timestamp_unix_nano: number; attributes: Record<string, unknown> }>;
  status: { code: string; description: string };
}

function _serialize(span: ReadableSpan): SerializedSpan {
  const ctx = span.spanContext();
  return {
    trace_id: ctx.traceId,
    span_id: ctx.spanId,
    parent_span_id: span.parentSpanId ?? null,
    name: span.name,
    kind: String(span.kind),
    start_time_unix_nano: span.startTime[0] * 1e9 + span.startTime[1],
    end_time_unix_nano: span.endTime[0] * 1e9 + span.endTime[1],
    attributes: { ...span.attributes },
    events: span.events.map(e => ({
      name: e.name,
      timestamp_unix_nano: e.time[0] * 1e9 + e.time[1],
      attributes: { ...(e.attributes ?? {}) },
    })),
    status: { code: String(span.status.code), description: span.status.message ?? "" },
  };
}

export class AgentAidSpanExporter implements SpanExporter {
  constructor(public endpoint = process.env.AGENTAID_ENDPOINT ?? "http://localhost:8000/ingest") {}

  export(spans: ReadableSpan[], cb: (result: ExportResult) => void): void {
    const payload = { spans: spans.map(_serialize) };
    fetch(this.endpoint, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(() => cb({ code: ExportResultCode.SUCCESS }))
      .catch((err) => cb({ code: ExportResultCode.FAILED, error: err as Error }));
  }

  async shutdown(): Promise<void> { /* fetch is fire-and-forget; nothing to clean */ }
}
```

- [ ] **Step 6: Eval models + define**

`packages/agentaid-ts/src/eval/models.ts`:

```typescript
import { z } from "zod";

export const EvalMode = {
  Online: "online",
  Regression: "regression",
  Invariant: "invariant",
} as const;
export type EvalMode = typeof EvalMode[keyof typeof EvalMode];

export const RunSchema = z.object({
  id: z.string(),
  agentName: z.string(),
  startedAt: z.string(),
  input: z.record(z.unknown()).nullable().default(null),
  output: z.record(z.unknown()).nullable().default(null),
  totalCost: z.number().default(0),
  totalTokens: z.number().default(0),
});
export type Run = z.infer<typeof RunSchema>;

export const EvalResultSchema = z.object({
  runId: z.string(),
  evalName: z.string(),
  mode: z.enum([EvalMode.Online, EvalMode.Regression, EvalMode.Invariant]),
  score: z.number().min(0).max(1),
  label: z.string().optional(),
  rationale: z.string().optional(),
});
export type EvalResult = z.infer<typeof EvalResultSchema>;

export const GoldenSchema = z.object({
  id: z.string(),
  input: z.record(z.unknown()),
  expected: z.record(z.unknown()),
});
export type Golden = z.infer<typeof GoldenSchema>;
```

`packages/agentaid-ts/src/eval/define.ts`:

```typescript
import { type Run, type Golden, type EvalResult, EvalMode } from "./models";

export { Run, Golden, EvalResult, EvalMode };

export type EvalFn = (run: Run, golden: Golden | null) => Promise<EvalResult>;

export interface EvalSpec {
  name: string;
  mode: EvalMode;
  judgeModel?: string;
  fn: EvalFn;
}

const _registry = new Map<string, EvalSpec>();

export function defineEval(spec: EvalSpec): void {
  if (_registry.has(spec.name)) {
    throw new Error(`eval '${spec.name}' is already registered`);
  }
  _registry.set(spec.name, spec);
}

export function getEval(name: string): EvalSpec {
  const spec = _registry.get(name);
  if (!spec) throw new Error(`eval '${name}' not registered`);
  return spec;
}

export function listEvals(): string[] {
  return [..._registry.keys()].sort();
}

export function evalsForMode(mode: EvalMode): EvalSpec[] {
  return [..._registry.values()].filter((s) => s.mode === mode);
}

/** @internal */
export function _resetForTests(): void { _registry.clear(); }
```

- [ ] **Step 7: Invariants helper**

`packages/agentaid-ts/src/eval/invariants.ts`:

```typescript
import { evalsForMode, EvalMode, type Run, type EvalResult } from "./define";

export async function runInvariants(run: Run): Promise<EvalResult[]> {
  const specs = evalsForMode(EvalMode.Invariant);
  const results: EvalResult[] = [];
  for (const spec of specs) {
    try {
      results.push(await spec.fn(run, null));
    } catch (err) {
      // emit failure as score 0 with rationale; don't throw across the loop
      results.push({
        runId: run.id, evalName: spec.name, mode: EvalMode.Invariant,
        score: 0, label: "error",
        rationale: err instanceof Error ? err.message : String(err),
      });
    }
  }
  return results;
}
```

- [ ] **Step 8: Index re-exports**

`packages/agentaid-ts/src/index.ts`:

```typescript
export { GenAI, AgentAid } from "./otel/conventions";
export { AgentAidSpanExporter } from "./otel/exporter";
export { defineEval, getEval, listEvals, evalsForMode, EvalMode } from "./eval/define";
export type { Run, Golden, EvalResult, EvalSpec, EvalFn } from "./eval/define";
export { runInvariants } from "./eval/invariants";
```

- [ ] **Step 9: Run tests + typecheck + build**

```bash
pnpm install
pnpm --filter agentaid typecheck
pnpm --filter agentaid test
pnpm --filter agentaid build
```

Expected: all green.

- [ ] **Step 10: Commit and close**

```bash
git add packages/agentaid-ts
git commit -m "add typescript sdk with otel exporter and eval defn"
bd close <id>
```

---

## Phase 9 — Bare-SDK Example (Day 7 part 3, ~3h)

### Task 28: Bare Anthropic SDK example with manual otel/genai

**Goal:** A small standalone example that uses the raw Anthropic SDK + manual OTel/GenAI instrumentation, ingested by the same AgentAid server. Proves AgentAid is framework-agnostic.

**Files:**
- Create: `packages/bare-sdk-example/src/example.py`
- Create: `packages/bare-sdk-example/README.md`
- Test: `packages/bare-sdk-example/tests/test_example.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 28: bare anthropic sdk example with manual otel" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Implement example**

`packages/bare-sdk-example/src/example.py`:

```python
"""A minimal agent loop using the Anthropic SDK directly + manual OTel/GenAI
instrumentation, ingested by AgentAid.

Demonstrates:
- Drop-in instrumentation with no agent framework
- Tool-use via Anthropic's `messages` API
- Run/role/agent_name attributes following AgentAid conventions
"""
from __future__ import annotations
import asyncio
import json
import uuid
from typing import Any
from anthropic import AsyncAnthropic
from opentelemetry import trace
from agentaid.otel import install as install_otel
from agentaid.otel.conventions import GenAI, AgentAid

TOOLS = [
    {
        "name": "search_arxiv",
        "description": "Mock search returning a couple of paper ids.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}},
                         "required": ["query"]},
    },
]

def _tool_dispatch(name: str, args: dict[str, Any]) -> str:
    if name == "search_arxiv":
        return json.dumps([
            {"id": "2401.00001", "title": "ADWIN-2"},
            {"id": "2402.00012", "title": "Page-Hinkley revisited"},
        ])
    return ""

async def run(research_interest: str) -> str:
    install_otel()
    tracer = trace.get_tracer("bare-sdk-example")
    run_id = f"bare-{uuid.uuid4().hex[:10]}"
    client = AsyncAnthropic()

    with tracer.start_as_current_span("agent") as root:
        root.set_attribute(AgentAid.RUN_ID, run_id)
        root.set_attribute(AgentAid.AGENT_NAME, "bare-sdk-example")
        root.set_attribute(AgentAid.ROLE, "agent")
        root.set_attribute(AgentAid.INPUT, json.dumps({"research_interest": research_interest}))

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": f"Find 1-2 papers on: {research_interest}. Use the search_arxiv tool."}
        ]
        for _ in range(3):  # bound the loop
            with tracer.start_as_current_span("model.call") as cs:
                cs.set_attribute(GenAI.SYSTEM, "anthropic")
                cs.set_attribute(GenAI.REQUEST_MODEL, "claude-haiku-4-5")
                cs.set_attribute(GenAI.OPERATION_NAME, "chat")
                resp = await client.messages.create(
                    model="claude-haiku-4-5", max_tokens=512,
                    tools=TOOLS, messages=messages,
                )
                cs.set_attribute(GenAI.RESPONSE_MODEL, resp.model)
                cs.set_attribute(GenAI.USAGE_INPUT_TOKENS, resp.usage.input_tokens)
                cs.set_attribute(GenAI.USAGE_OUTPUT_TOKENS, resp.usage.output_tokens)
            if resp.stop_reason == "tool_use":
                tool_uses = [b for b in resp.content if b.type == "tool_use"]
                tool_results = []
                for tu in tool_uses:
                    with tracer.start_as_current_span(tu.name) as ts:
                        ts.set_attribute(AgentAid.RUN_ID, run_id)
                        ts.set_attribute(AgentAid.ROLE, "tool")
                        ts.set_attribute(GenAI.TOOL_NAME, tu.name)
                        out = _tool_dispatch(tu.name, dict(tu.input or {}))
                        tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": out})
                messages.append({"role": "assistant", "content": resp.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                final_text = "".join(b.text for b in resp.content if b.type == "text")
                root.set_attribute(AgentAid.OUTPUT, json.dumps({"answer": final_text}))
                return final_text
        return "(loop exhausted)"

if __name__ == "__main__":
    print(asyncio.run(run("concept drift in streaming ML")))
```

- [ ] **Step 3: README**

`packages/bare-sdk-example/README.md`:

```markdown
# bare-sdk-example

A minimal agent loop using the Anthropic SDK directly + manual OpenTelemetry/GenAI instrumentation.

Run:
```
AGENTAID_ENDPOINT=http://localhost:8000/ingest \
  uv run python -m bare_sdk_example.example
```

This sends spans to AgentAid using the same ingestion path as the Pydantic-AI reference agent — proof of framework-agnostic ingestion.
```

- [ ] **Step 4: Smoke test**

`packages/bare-sdk-example/tests/test_example.py`:

```python
import pytest

@pytest.mark.live
@pytest.mark.asyncio
async def test_bare_example_returns_text() -> None:
    from bare_sdk_example.example import run
    out = await run("a small test interest")
    assert isinstance(out, str)
    assert out
```

(Update `pyproject.toml` so the package name maps `bare_sdk_example` to the src; rename the directory to `src/bare_sdk_example/example.py` and add `src/bare_sdk_example/__init__.py`.)

- [ ] **Step 5: Manual smoke**

```bash
AGENTAID_ENDPOINT=http://localhost:8000/ingest uv run python -m bare_sdk_example.example
sleep 2
curl -s "http://localhost:8000/runs?limit=5" | python -m json.tool | grep "bare-"
```

Expected: a `bare-...` run id appears.

- [ ] **Step 6: Commit and close**

```bash
git add packages/bare-sdk-example
git commit -m "add bare anthropic sdk example with manual otel"
bd close <id>
```

---

## Phase 10 — Real arXiv API (Day 7 part 4, ~4h)

### Task 29: Real arXiv API behind feature flag

**Goal:** Implement the real arXiv client with the same shape as the mock, behind `AGENTAID_USE_REAL_ARXIV=1`. Default remains the mock. Includes rate-limit politeness and basic caching.

**Files:**
- Create: `packages/reference-agent/src/arxiv_agent/mock_arxiv/real.py`
- Test: `packages/reference-agent/tests/test_real_arxiv.py`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 29: real arxiv client behind feature flag" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Failing test (network-marked)**

`packages/reference-agent/tests/test_real_arxiv.py`:

```python
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
    from arxiv_agent.mock_arxiv.client import get_arxiv_client
    from arxiv_agent.mock_arxiv.real import RealArxivClient
    assert isinstance(get_arxiv_client(), RealArxivClient)
```

Run: `uv run pytest packages/reference-agent/tests/test_real_arxiv.py::test_get_arxiv_client_returns_real_when_flag_set -v` → FAIL.

- [ ] **Step 3: Implement real client**

`packages/reference-agent/src/arxiv_agent/mock_arxiv/real.py`:

```python
from __future__ import annotations
import time
import functools
from urllib.parse import urlencode
import httpx
import feedparser
from .mock import PaperSummary, Paper, Figure

ARXIV_API = "http://export.arxiv.org/api/query"

class RealArxivClient:
    """Real arXiv client. Polite by default: 3-second delay between requests,
    in-process cache, falls back to mock for figure extraction (real figure
    extraction from arXiv PDFs is out of scope for this iteration).
    """
    def __init__(self, min_delay_s: float = 3.0, timeout_s: float = 15.0) -> None:
        self.min_delay = min_delay_s
        self._last_call = 0.0
        self._client = httpx.Client(timeout=timeout_s,
                                    headers={"User-Agent": "AgentAid/0.0 (portfolio project)"})
        # Reuse mock figures so the multi-modal pipeline still has data when the real
        # API is in use; documenting honestly in README.
        from .mock import MockArxivCore
        self._fallback = MockArxivCore()

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self._last_call = time.monotonic()

    @functools.lru_cache(maxsize=128)
    def _query(self, params_tuple: tuple[tuple[str, str], ...]) -> str:
        self._wait()
        url = ARXIV_API + "?" + urlencode(dict(params_tuple))
        r = self._client.get(url)
        r.raise_for_status()
        return r.text

    def search(self, query: str, limit: int = 10,
               date_from: str | None = None, date_to: str | None = None) -> list[PaperSummary]:
        params = (("search_query", f"all:{query}"),
                  ("start", "0"),
                  ("max_results", str(limit)),
                  ("sortBy", "submittedDate"),
                  ("sortOrder", "descending"))
        raw = self._query(params)
        feed = feedparser.parse(raw)
        out: list[PaperSummary] = []
        for entry in feed.entries[:limit]:
            published = entry.get("published", "")[:10]
            if date_from and published < date_from: continue
            if date_to and published > date_to: continue
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
            id=paper_id, title=e.get("title", "").strip(),
            authors=tuple(a.get("name", "") for a in e.get("authors", [])),
            abstract=e.get("summary", "").strip(),
            published=e.get("published", "")[:10],
            categories=tuple(t.get("term", "") for t in e.get("tags", [])),
        )

    def fetch_paper(self, paper_id: str) -> Paper:
        # Full text fetch via PDF parsing is non-trivial; fall back to abstract + metadata.
        meta = self.fetch_metadata(paper_id)
        return Paper(id=meta.id, title=meta.title, authors=meta.authors,
                     abstract=meta.abstract, published=meta.published,
                     categories=meta.categories,
                     body=meta.abstract)  # body is the abstract for the real-API path

    def extract_figures(self, paper_id: str) -> list[Figure]:
        # Reuse mock figures; honestly noted in README.
        return self._fallback.extract_figures(paper_id)
```

- [ ] **Step 4: Run validation test, expect PASS**

```bash
AGENTAID_USE_REAL_ARXIV=1 uv run pytest packages/reference-agent/tests/test_real_arxiv.py::test_get_arxiv_client_returns_real_when_flag_set -v
```

- [ ] **Step 5: Live smoke (one shot, polite)**

```bash
uv run python -c "
from arxiv_agent.mock_arxiv.real import RealArxivClient
c = RealArxivClient()
for p in c.search('concept drift', limit=2):
    print(p.id, '-', p.title)
"
```

Expected: 1–2 actual arXiv ids and titles, no rate-limit errors.

- [ ] **Step 6: Commit and close**

```bash
git add packages/reference-agent
git commit -m "add real arxiv client behind feature flag"
bd close <id>
```

---

## Phase 11 — Polish (Day 8, ~6h)

### Task 30: CI workflow

**Goal:** GitHub Actions workflow runs type-check, tests, and lint on push and PR. Single workflow, parallel jobs.

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 30: github actions ci" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Workflow**

`.github/workflows/ci.yml`:

```yaml
name: ci
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }

jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with: { version: "0.4.x" }
      - run: uv sync
      - run: uv run ruff check .
      - run: uv run mypy packages/agentaid-py/src packages/agentaid-server/src packages/reference-agent/src
      - run: uv run pytest -m "not live" --maxfail=5

  typescript:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - uses: pnpm/action-setup@v4
        with: { version: 9 }
      - run: pnpm install
      - run: pnpm -r typecheck
      - run: pnpm -r lint
      - run: pnpm -r test
```

- [ ] **Step 3: Verify locally before pushing**

```bash
make typecheck
make test
make lint
```

(Mark slow / live tests with `@pytest.mark.live` so CI's `not live` filter excludes them — apply consistently across the test files written so far.)

- [ ] **Step 4: Commit and close**

```bash
git add .github
git commit -m "add github actions ci for python and typescript"
bd close <id>
```

---

### Task 31: README narrative + screenshots

**Goal:** A README that opens with the platform's thesis in one paragraph, embeds a recorded video at the top, walks through the architecture, names the engineering decisions made, and ends with "what's next." Includes 4–6 screenshots from the running app.

**Files:**
- Modify: `README.md`
- Create: `docs/screenshots/*.png`

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 31: readme narrative + screenshots" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Capture 4–6 screenshots**

Run:

```bash
make server &
make web &
uv run python scripts/load_golden.py
uv run python scripts/seed_drift.py
sleep 6   # let drift workers tick
```

Open the app and capture (use OS screenshot tooling):

1. `docs/screenshots/01-drift-home.png` — `/` showing all three drift signals firing.
2. `docs/screenshots/02-trace-gantt.png` — `/runs/<id>` showing the Gantt for a planner+worker run.
3. `docs/screenshots/03-run-comparison.png` — `/compare?a=...&b=...` showing the scorecard and tool-call distribution shift.
4. `docs/screenshots/04-drift-detail.png` — `/drift/quality` showing the time-series with the threshold line.
5. `docs/screenshots/05-eval-results.png` — `/evals` showing the four sparklines.
6. `docs/screenshots/06-architecture.png` — a hand-drawn or `excalidraw` system diagram.

- [ ] **Step 3: Author README**

`README.md`:

```markdown
# AgentAid

> A drift-aware observability and evaluation platform for production AI agents,
> built around the thesis that distribution drift — on agent inputs, tool-call
> patterns, and eval scores — is a first-class signal that traces and metrics
> alone don't surface.

[▶ 5-minute walkthrough video](https://youtu.be/<id>) <!-- link recorded in Task 32 -->

![Drift home](docs/screenshots/01-drift-home.png)

## What this is

AgentAid ingests OpenTelemetry traces using the GenAI semantic conventions
(`gen_ai.*` and `agentaid.*` attributes) and runs three first-class systems on
top:

- **Trace storage** — runs, spans, and tool-call structure, queryable via REST.
- **Eval framework** — three operating modes (online sampled, offline regression,
  trace invariants) on a single typed definition surface; four built-in templates.
- **Drift detection** — three signals (input embeddings, tool-call distribution,
  eval-score quality) with pluggable detectors (ADWIN, MMD, PSI today).

The included **arXiv research agent** is the reference workload — a multi-agent
(planner + worker) pipeline with multi-modal figure extraction, used to exercise
the platform on real-shaped traffic and to drive the demo.

## Architecture

![Architecture](docs/screenshots/06-architecture.png)

Three layers, otel/genai at the seam between them:

1. **Agent + SDK layer** — Pydantic AI reference agent and a bare-Anthropic-SDK
   example. Both emit OTel/GenAI spans via the `agentaid` Python or TypeScript SDK.
2. **Server layer** — FastAPI + SQLModel + SQLite. Ingests spans, runs LLM-judge
   evals async, runs three drift-detector workers on a 5-second tick.
3. **Frontend layer** — Vite + React + TypeScript. Drift-first home, Gantt trace
   detail, summary-led run comparison, drift detail × 3.

## Why these choices

- **OTel + GenAI conventions** instead of a vendor format → AgentAid is reusable
  on any agent stack; the bare-SDK example proves it.
- **Pydantic AI** for the reference agent → typed end-to-end, async-native, thin
  enough to debug into and instrument cleanly.
- **Hand-rolled ADWIN/MMD/PSI** instead of `scikit-multiflow` → the math is
  visible and the dependency footprint stays small.
- **Eval-first orchestration** → eval results are first-class typed objects;
  drift detectors subscribe to eval streams, so quality drift is wired to the
  same numbers a developer reasons about.

## Quick start

```bash
make install
make server   # http://localhost:8000
make web      # http://localhost:5173
uv run python scripts/load_golden.py
uv run python scripts/seed_drift.py   # makes drift visibly fire in the demo
```

To run the agent end-to-end against the AgentAid server:

```bash
AGENTAID_ENDPOINT=http://localhost:8000/ingest uv run python -m arxiv_agent
```

To run the bare-Anthropic-SDK example through the same ingestion pipeline:

```bash
AGENTAID_ENDPOINT=http://localhost:8000/ingest uv run python -m bare_sdk_example.example
```

## Screenshots

| Drift home | Trace detail (Gantt) | Run comparison |
|---|---|---|
| ![home](docs/screenshots/01-drift-home.png) | ![gantt](docs/screenshots/02-trace-gantt.png) | ![compare](docs/screenshots/03-run-comparison.png) |

## Out of scope (with rationale)

| Out | Why |
|---|---|
| Multi-tenancy / auth | Single-developer dev tool. |
| Real-time WebSocket streaming | Polling is sufficient for the demo. |
| Drift methods beyond ADWIN/MMD/PSI | Plugin interface designed for additions; demonstrating the interface matters more than method count. |
| Mobile-responsive UI | Reviewer is on a desktop. |
| Live deployment | Replaced by the recorded walkthrough above. |
| Prompt-versioning UI | Prompts are code, versioned in git, surfaced as SHAs. UI for editing them is low ROI. |
| OpenAI provider | Anthropic-only; otel/genai conventions and the bare-SDK example carry the framework-agnostic claim. |

## Repository layout

See `docs/superpowers/specs/2026-05-06-agentaid-design.md` for the full design,
and `docs/superpowers/plans/2026-05-06-agentaid-implementation.md` for the
plan that produced this implementation.

## License

MIT (see `LICENSE`).
```

- [ ] **Step 4: Commit and close**

```bash
git add README.md docs/screenshots
git commit -m "add readme with thesis, screenshots, and architecture"
bd close <id>
```

---

### Task 32: Recorded walkthrough

**Goal:** A 4–6 minute screen recording on YouTube (unlisted) walking through the platform's thesis, the agent run, drift detection firing, run comparison, and the bare-SDK example. Linked from the README's hero spot.

**Files:**
- Create: `scripts/run_demo.py` (driver that produces a clean, scripted demo run)
- Modify: `README.md` (insert real video URL once recorded)

- [ ] **Step 1: bd issue**

```bash
bd create --title="Task 32: recorded walkthrough video" --type=task --priority=2
bd update <id> --claim
```

- [ ] **Step 2: Write `scripts/run_demo.py`**

```python
"""Drive a clean, scripted demo of AgentAid for the recorded walkthrough.

Steps:
1. Load the golden dataset.
2. Seed synthetic drift.
3. Run two real agent invocations (different research interests) so there's
   live content alongside the seeded data.
4. Trigger a Mode 2 regression run.

Designed so you can record the screen while this runs in the background and
the UI updates live.
"""
from __future__ import annotations
import asyncio
import os
import subprocess
import time

async def _agent_run(interest: str) -> None:
    env = os.environ.copy()
    env["AGENTAID_ENDPOINT"] = env.get("AGENTAID_ENDPOINT", "http://localhost:8000/ingest")
    proc = await asyncio.create_subprocess_exec(
        "uv", "run", "python", "-m", "arxiv_agent", interest,
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    await proc.wait()

async def main() -> None:
    print("loading golden dataset…")
    subprocess.run(["uv", "run", "python", "scripts/load_golden.py"], check=True)
    print("seeding synthetic drift…")
    subprocess.run(["uv", "run", "python", "scripts/seed_drift.py"], check=True)
    print("running 2 live agent invocations…")
    await asyncio.gather(
        _agent_run("concept drift detection in streaming ML"),
        _agent_run("multi-agent orchestration with tool use"),
    )
    print("triggering regression…")
    subprocess.run([
        "curl", "-sS", "-X", "POST", "http://localhost:8000/regressions",
        "-H", "content-type: application/json",
        "-d", '{"dataset_id":"golden-arxiv-v1","prompt_sha":"HEAD","model":"claude-sonnet-4-6"}'
    ], check=True)
    print("done. record the UI now.")

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Record (manual, ~30–60 min including retakes)**

Suggested 6-section script for the screencast (≤6 minutes total):

1. **Hook (20s).** "AgentAid is a drift-aware obs/eval platform for production agents — three signals other tools don't surface."
2. **Drift home (45s).** Open `/`, point at the three signal cards, click into `/drift/quality` to show the time-series and threshold.
3. **A trace (60s).** Click a recent run; walk through the Gantt — point out planner span, parallel workers, tool calls; click the slow `extract_figures` span to show attributes; show the figure rendering.
4. **Eval framework (40s).** Open `/evals`. Show four sparklines. Note which two are LLM-judges and which two are deterministic invariants.
5. **Run comparison (60s).** Open `/compare?a=...&b=...`. Walk through the scorecard, the tool-call distribution shift, the drift contribution callout.
6. **Framework-agnostic (40s).** Run the bare-Anthropic-SDK example in a terminal; refresh `/runs` to show its `bare-...` run id appearing in the same UI.
7. **Close (15s).** "Github at <url>; design docs in `docs/superpowers/`."

Upload to YouTube as Unlisted. Capture the URL.

- [ ] **Step 4: Replace placeholder URL in README**

In `README.md`, replace `https://youtu.be/<id>` with the real URL.

- [ ] **Step 5: Commit and close**

```bash
git add README.md scripts
git commit -m "add demo driver and link recorded walkthrough"
bd close <id>
```

---

## Verification & Hand-off

When all 32 tasks are closed:

- [ ] All bd issues closed: `bd list --status=open` returns empty.
- [ ] `make test` passes (Python `not live` + TS).
- [ ] `make typecheck` passes.
- [ ] `make lint` passes.
- [ ] `make server` + `make web` boot cleanly; `/healthz` returns ok.
- [ ] After running `scripts/load_golden.py` + `scripts/seed_drift.py`, all three drift signals fire visibly in the UI.
- [ ] Bare-SDK example produces a visible run on `/runs`.
- [ ] README renders correctly on GitHub (screenshots load, video link works).
- [ ] Commit history is terse and informative; no `🤖 Generated with Claude Code` lines and no `Co-Authored-By` trailers.

