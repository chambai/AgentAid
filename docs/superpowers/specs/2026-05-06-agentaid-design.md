# AgentAid — Design

**Status:** draft v1 · 2026-05-06
**Owner:** Lorraine Chambers
**Audience:** future implementers (incl. AI coding agents) and reviewers of the portfolio submission

## Summary

AgentAid is a drift-aware observability and evaluation platform for production AI agents. Most agent obs tools (Langfuse, LangSmith, Phoenix, Helicone) treat traces and evals as the primary signals; AgentAid adds **distribution drift** as a first-class signal alongside them, on three axes: agent inputs, tool-call distribution, and eval quality. The platform ingests OpenTelemetry traces using the GenAI semantic conventions, so it is framework-agnostic and intended for reuse beyond this project.

A reference agent — a multi-agent (planner + worker) arXiv research assistant with multi-modal capability — exercises the platform on real-shaped traffic and supplies the demo material.

## Audience and goal

This is a portfolio project targeting senior AI engineering roles at companies that ship production AI agents to enterprise customers. The artifact is a public GitHub repo with a recorded video walkthrough; there is no live deployment in scope. The platform is the headline; the agent is the included reference workload that proves the platform on non-toy traffic.

What we are optimizing for, in order:

1. **A defensible thesis a reviewer can articulate after five minutes of skimming** ("drift-aware agent obs, three signals, framework-agnostic via otel/genai").
2. **Senior-engineer signals**: typed end-to-end, async, framework-agnostic, polyglot SDK (Python + TS), eval discipline, principled framework choice, multi-modal handled honestly.
3. **A working live experience in `dev` plus a clean recorded walkthrough** (no production deploy).

## Goals

- Demonstrate competence at building agent systems: planner+worker topology, tool use, multi-turn (agent-to-agent and human-to-agent), multi-modal (vision over paper figures).
- Demonstrate eval discipline: typed eval definitions, three operating modes (online sampled, offline regression, trace invariants), a small but real golden dataset.
- Demonstrate the drift-aware thesis: three distinct detectors (input/tool-call/quality) running on real traces, alarms reaching the UI, the math grounded in published methods (MMD, PSI, ADWIN).
- Demonstrate full-stack capability: Python SDK + server, TypeScript SDK + frontend, async throughout, types end-to-end.
- Stay credibly framework-agnostic: ingest OpenTelemetry/GenAI spans, ship a working bare-Anthropic-SDK example alongside the Pydantic AI reference.

## Non-goals (explicit)

| Out of scope | Rationale |
|---|---|
| Multi-tenancy / auth | Single-developer dev tool. Out of scope for portfolio. |
| Real-time WebSocket trace streaming | Polled refresh is fine for the demo and saves real engineering. |
| Drift methods beyond ADWIN / MMD / PSI (one per signal) | Plugin interface allows future additions; demonstrating the interface matters more than method count. |
| Mobile-responsive UI | Reviewer is on a desktop. |
| Internationalization | Not relevant. |
| Live deployment | Replaced by recorded video on the GitHub README. |
| Prompt-versioning UI in-app | Prompts are code, versioned in git, surfaced as SHAs in run comparison. UI for editing them is low ROI. |
| OpenAI provider | Anthropic-only is defensible; otel/genai conventions + the bare-SDK example carry the framework-agnostic claim. |
| Streaming chat UI for the agent | The frontend is the obs/eval dashboard, not a chat surface. |

## Thesis

The platform is the headline — AgentAid is what someone reuses on their next agent project. The arXiv research agent is the reference workload that supplies real traces and a demo, and naturally exhibits all three drift signals over time (paper distributions shift, retrieval/tool patterns shift, eval scores shift). The reference agent is engineered well enough to be credible on its own, but the headline reads "I built the obs/eval platform; here's an agent showing it works."

## High-level architecture

```
┌──────────────────────┐    ┌────────────────────────────────────┐    ┌─────────────────────────┐
│  Reference agent     │    │  AgentAid server (FastAPI)         │    │  AgentAid web (Vite/TS) │
│  (Pydantic AI)       │    │                                    │    │                         │
│  ┌────────────────┐  │    │  ┌──────────────────────────────┐  │    │  ┌───────────────────┐  │
│  │ Planner agent  │  │    │  │ otel/genai ingestion         │  │    │  │ Drift home        │  │
│  │ Worker agent   │──┼────┼─▶│ Run + span store (SQLite)    │◀─┼────┼──│ Trace (Gantt)     │  │
│  │ Tools (×8)     │  │    │  │ Eval orchestrator (Mode 1/2) │  │    │  │ Run comparison    │  │
│  └────────────────┘  │    │  │ Drift workers (3 signals)    │  │    │  │ Drift detail × 3  │  │
│  Mock arXiv (default)│    │  │ REST API                     │  │    │  │ Eval / datasets   │  │
└─────▲────────────────┘    │  └──────────────────────────────┘  │    │  └───────────────────┘  │
      │ otel exporter                                           ▲│    └─────────▲───────────────┘
      │ (Python)                                                ││              │ REST + polling
      │                                                         ││              │
┌─────┴────────────────┐                                        ││    ┌─────────┴───────────────┐
│ AgentAid Python SDK  │                                        ││    │ AgentAid TS SDK         │
│ - otel/genai exporter│                                        ││    │ - otel/genai exporter   │
│ - eval defn + runner │                                        ││    │ - eval defn (builder)   │
│ - drift detectors    │                                        ││    │ - trace invariants      │
│ - eval templates     │                                        ││    │ (no drift; server-side) │
└──────────────────────┘                                        ││    └─────────────────────────┘
                                                                ││
┌────────────────────────────┐                                  ││
│ Bare-Anthropic-SDK example │ ──── manual otel/genai spans ────┘│
│ (proves framework-agnostic)│                                   │
└────────────────────────────┘                                   │
                                                                 │
                                       Same ingestion path ──────┘
```

Three layers:

1. **Agent + SDK layer.** The reference agent (Pydantic AI on Anthropic) and the bare-Anthropic-SDK example. Both emit OpenTelemetry spans following GenAI semantic conventions. The SDKs (Python and TypeScript) provide instrumentation helpers, eval-definition surface, and drift-detector base classes. *Nothing* in this layer talks to the AgentAid server through a vendor-specific protocol — only through otel/genai.
2. **Server layer.** FastAPI app. Ingests otel/genai spans. Stores runs, spans, eval results, drift signals in SQLite. Runs LLM-judge evals async. Hosts drift-detector workers that subscribe to eval and trace-invariant streams. Exposes a REST API.
3. **Frontend layer.** Vite + React + TypeScript. Drift-first home, Gantt trace detail, summary-led run comparison, drift detail pages × 3, eval results, datasets. Polls the server (no WS streaming in scope).

## Components

### Reference agent — `packages/reference-agent`

**Framework:** Pydantic AI on the Anthropic provider.

**Topology:** Planner + Worker (multi-agent). Synthesis is a final step inside the planner — no third agent — to keep the topology honest.

**Roles and tools:**

- **Planner.** Decides which candidate papers deserve deep reading and assembles the final digest.
  - `search_arxiv(query, date_range)`
  - `fetch_metadata(paper_id)`
  - `score_candidate(metadata, criteria)`
  - `compose_digest(papers)` *(final synthesis call)*
- **Worker.** Per-paper deep read, with multi-modal figure extraction.
  - `fetch_paper(paper_id)`
  - `extract_figures(paper_id)` *(VLM call — multi-modal)*
  - `summarize(content, focus)`
  - `query_paper(paper_id, question)` *(used in human Q&A mode)*

**Multi-turn modes:**

- *Agent-to-agent.* Planner spawns multiple workers (potentially in parallel), can replan after worker results.
- *Human-to-agent.* After a digest is produced, the user can ask follow-up questions about a specific paper. The Q&A invocation reuses the worker with the paper's context.

**Prompts:** `packages/reference-agent/prompts/*.md`, loaded by name at runtime, version-controlled in git, surfaced in trace metadata as the file's git SHA.

**Mock arXiv layer:** `packages/reference-agent/mock_arxiv/`. Deterministic, ships a small canned corpus (10–20 papers with abstracts, full text excerpts, and a few JPEG figures suitable for vision input). Default for development. Real arXiv API behind `AGENTAID_USE_REAL_ARXIV=1`, with rate-limit and politeness handling.

### AgentAid Python SDK — `packages/agentaid-py`

**Provides:**

- **otel/genai exporter helpers.** Thin wrapper that configures an OTel tracer with the GenAI conventions and ships spans to the AgentAid server (HTTP + protobuf or HTTP + JSON; final wire format decided in plan-time).
- **Eval definition surface.** Decorator-based:

  ```python
  @agentaid.eval(name="digest_relevance", mode="online", judge_model="claude-haiku-4-5")
  async def relevance(run: Run, golden: Golden | None = None) -> EvalResult: ...
  ```

  All three modes share this surface. `mode="online"` means sampled-on-every-run (server-side execution). `mode="regression"` means dataset-driven (server-side, batch). `mode="invariant"` means deterministic, in-process (no LLM, runs in the SDK, emits a span event).

- **Drift detector framework.** Abstract base class plus three concrete detectors. Detectors run server-side (cross-run analysis), but the abstract class lives in the SDK so users can author and register custom detectors that the server picks up.

  ```python
  class DriftDetector(Protocol):
      def update(self, value: float) -> None: ...
      def is_drifted(self) -> bool: ...
      def state(self) -> DriftState: ...
  ```

- **Eval templates** (4 built-ins): `relevance_judge`, `faithfulness_judge`, `structural_completeness`, `cost_within_budget`.

**Implementation notes:**

- ADWIN and Page-Hinkley via `scikit-multiflow` (or hand-rolled minimal versions if dependency cost is too high — decided in plan-time).
- MMD via `scipy` + `numpy`.
- PSI hand-rolled (~30 lines).
- Python 3.12+, Pydantic v2, async-throughout.

### AgentAid TypeScript SDK — `packages/agentaid-ts`

**Provides:**

- **otel/genai exporter helpers.** TS-native equivalent of the Python exporter, using `@opentelemetry/sdk-trace-node` and the GenAI conventions.
- **Eval definition surface (builder, since TS has no decorators in stable form):**

  ```typescript
  agentaid.defineEval({
    name: "digest_relevance",
    mode: "online",
    judgeModel: "claude-haiku-4-5",
    fn: async (run, golden) => ({ score: ..., label: ..., rationale: ... }),
  });
  ```

  Eval *definitions* are typed with Zod schemas; eval *execution* for LLM judges happens server-side.
- **Trace invariants** (Mode 3) execute in-process, emit span events.

**Out of scope for the TS SDK:** drift detection (server-side only), prompt loading helpers, multimodal helpers (the bare-SDK example demonstrates these in TS only if the user explicitly wants — currently planned to demonstrate them in Python only).

### Bare-Anthropic-SDK example — `packages/bare-sdk-example`

A small, working agent built directly on `anthropic-sdk-python` with manual otel/genai instrumentation. Single-file or near-single-file. Same ingestion pipeline. Demonstrates that AgentAid is *actually* framework-agnostic — not just a Pydantic AI tool with otel branding.

### AgentAid server — `packages/agentaid-server`

**Stack:** FastAPI + SQLModel (SQLAlchemy 2.0 async) + SQLite. Single process. No Redis, no message queue — async tasks via FastAPI background tasks or a tiny in-process worker loop.

**Surfaces:**

- **Ingestion endpoint.** Accepts otel/genai spans (HTTP). Writes to `spans` and reconstructs/upserts `runs`.
- **REST API.** Endpoints for: list runs (search/filter), get run + spans, list evals, eval results per run, run comparison, drift status (per signal), drift series (time-windowed for charts), datasets, trigger Mode 2 regression.
- **Eval orchestrator.** Watches new runs; for each, schedules its applicable Mode 1 evals; writes `eval_results`. Mode 2 runs on demand via API.
- **Drift workers.** Three workers (one per signal). Subscribe (in-process pub/sub or polling) to new eval results and trace invariants. Update detector state, write `drift_state` snapshots, raise alerts.

**Storage schema (sketch — final ERD in plan-time):**

- `runs` (id, agent_name, started_at, ended_at, status, prompt_sha, model, total_cost, total_tokens)
- `spans` (id, run_id, parent_span_id, name, role, started_at, ended_at, attributes_json, events_json)
- `eval_results` (id, run_id, eval_name, mode, score, label, rationale, created_at)
- `datasets` (id, name, description, schema_json) + `dataset_rows` (id, dataset_id, input_json, expected_json)
- `regression_runs` (id, dataset_id, prompt_sha, model, started_at, ended_at, status, summary_json)
- `drift_state` (id, signal, detector_name, window, value, threshold, is_drifted, updated_at)
- `drift_events` (id, signal, detector_name, started_at, ended_at, severity, contributing_run_ids_json)

### Frontend — `packages/agentaid-web`

**Stack:** Vite + React + TypeScript. TanStack Query for server state. React Router. Charts: `recharts` (preferred for accessibility and small bundle) or `visx` (decided in plan-time based on Gantt requirements).

**Pages:**

- **Drift home (`/`).** Three signal cards (input / tool-call / quality) with current state and 7-day trend, recent runs list. *Hero of the platform's thesis.*
- **Trace detail (`/runs/:id`).** Gantt timeline of planner + worker spans with drift contribution band, span detail panel on click, image attachments rendered for multi-modal spans.
- **Run comparison (`/compare?a=:id&b=:id`).** Summary-led: scorecard at top (relevance, faithfulness, cost, latency), tool-call distribution shift in the middle, drift contribution callout, expandable Gantt overlay / output diff / span-level diff.
- **Drift detail (`/drift/:signal`)** — three pages, one per signal. Time-series of the metric, current vs reference distribution visualization (histogram for input/quality; bar chart for tool-call), recent contributing runs.
- **Eval results (`/evals`).** Table of online evals with sparkline scores, link-through to traces. Mode 2 regression report with pass/fail per row.
- **Datasets (`/datasets`).** List datasets, view rows, run a Mode 2 regression against a chosen prompt SHA.
- **Run list / search (`/runs`).** Search by query, tool, score, time. Default sort: most recent.

**Out of frontend scope:** real-time streaming, mobile, prompt editing, dataset editing in-app.

## Data flow

**Standard run:**

1. Agent emits otel/genai spans → SDK exporter ships to server's ingestion endpoint.
2. Server writes spans, upserts the run record, evaluates trace invariants (Mode 3) inline.
3. Server enqueues Mode 1 evals for the run (LLM-judge calls run async).
4. Eval-result writes trigger drift-detector workers; detectors update state and may raise drift events.
5. Frontend reads via REST endpoints, polls for liveness updates.

**Mode 2 regression:**

1. User triggers a regression run via API/UI: `(dataset_id, prompt_sha, model)`.
2. Server iterates dataset rows, calls the agent, ingests the resulting traces.
3. Per-row reference-based evals run (using the `golden` arg in the eval surface).
4. Aggregate results land in `regression_runs.summary_json` and per-row `eval_results`.

## Drift detection design

| Signal | Detector | Method | Inputs |
|---|---|---|---|
| **Input drift** | `EmbeddingMmdDetector` | MMD between recent window of query embeddings vs reference window | Query/user-input strings → embedding (Anthropic or local sentence-transformers; decided in plan-time, default Anthropic for one less dep) |
| **Tool-call distribution drift** | `ToolCallPsiDetector` | Population Stability Index on tool-call frequency distribution per agent role | Span events: tool name + role |
| **Quality drift** | `EvalScoreAdwinDetector` | ADWIN online change-detection on a target eval score | `eval_results.score` for `digest_relevance` (and optionally `faithfulness`) |

**Pluggability:** detectors implement the `DriftDetector` protocol. Server discovers detectors via a registry (decorator on the class). Adding a new method = a new class + entry in the config; no platform changes needed.

**Calibration:** `scripts/seed_drift.py` produces synthetic time-windowed inputs designed to deliberately trigger each detector, used for demo and integration tests. Without this, drift wouldn't reliably fire in a 7-day budget.

## Eval framework design

**Three modes, single definition surface:**

- **Mode 1 (online)** — server-side, async, sampled per run. LLM-judge or any non-deterministic eval. Feeds quality drift.
- **Mode 2 (offline regression)** — server-side, batch, dataset-driven. Reference-based scoring. Used to compare prompt SHAs / models.
- **Mode 3 (trace invariants)** — in-process, fast, deterministic. No LLM. Runs in the SDK at trace boundaries; emits span events. Feeds tool-call drift indirectly via structured tool-call data.

**Built-in templates** (ship with the Python SDK):

- `relevance_judge` (LLM judge, online) — does the digest answer the user's research interest?
- `faithfulness_judge` (LLM judge, online) — does the digest stay faithful to retrieved papers?
- `structural_completeness` (invariant, Mode 3) — every paper in the digest has a summary, score, and citation.
- `cost_within_budget` (invariant, Mode 3) — run cost ≤ configured threshold.

**Definition surface example** (Python; TS uses a builder of equivalent shape):

```python
@agentaid.eval(name="digest_relevance", mode="online", judge_model="claude-haiku-4-5")
async def relevance(run: Run, golden: Golden | None = None) -> EvalResult:
    digest = run.output["digest"]
    interest = run.input["research_interest"]
    return await llm_judge(
        instructions="Score 0-1 how well the digest matches the research interest.",
        run_input=interest,
        run_output=digest,
    )
```

## Repo layout

```
agentaid/
├── README.md                       # narrative arc + screenshots + video
├── docs/superpowers/specs/         # this design doc + future ones
├── packages/
│   ├── agentaid-py/                # Python SDK (eval, drift, otel/genai)
│   ├── agentaid-ts/                # TS SDK (npm package)
│   ├── agentaid-server/            # FastAPI server
│   ├── agentaid-web/               # Vite + React + TS frontend
│   ├── reference-agent/            # Pydantic AI arXiv agent + mock layer
│   └── bare-sdk-example/           # Bare Anthropic SDK + manual otel
├── eval/golden/                    # 10–15 row golden dataset (JSON)
├── scripts/
│   ├── seed_drift.py               # Synthetic drift seed + calibration
│   └── run_demo.py                 # End-to-end demo driver for the video
├── pyproject.toml                  # Workspace root (uv or rye)
├── package.json                    # JS/TS workspace root (pnpm)
└── .github/workflows/ci.yml        # Type-check + tests + lint
```

## Testing strategy

- **Python unit tests (pytest).** Drift detectors against synthetic streams (deterministic). Eval framework dispatch and template behavior. Mock arXiv layer.
- **Python integration tests.** Server endpoints with a live-but-isolated SQLite. Ingest → run → eval flow.
- **TS unit tests (vitest).** SDK instrumentation: assert that emitted spans match the otel/genai shape. Trace invariants.
- **Frontend.** Type-check pass + a couple of smoke tests via Vitest + Testing Library on the home page and one trace detail. No exhaustive component tests (out of scope).
- **CI.** GitHub Actions: type-check (mypy strict, tsc strict), pytest, vitest, ruff, eslint. Single workflow, parallel jobs.

## Scope and timeline

| Day | ~Hours | Focus |
|---|---|---|
| 1 | 12 | Repo + monorepo scaffold; Pydantic AI agent skeleton; mock arXiv; one tool flowing end-to-end; otel exporter emitting first spans. |
| 2 | 12 | Reference agent fully wired (planner + worker, all 8 tools incl. multi-modal `extract_figures`); golden dataset (10–15 rows). |
| 3 | 12 | FastAPI server: ingestion endpoint, run/span storage (SQLite via SQLModel), basic REST. |
| 4 | 12 | Frontend scaffold (Vite + React + TS); drift-first home page; Gantt trace detail (live data). |
| 5 | 12 | Eval framework + 4 templates + Mode 1 (online) + Mode 3 (invariants); LLM judge runner async; start TS SDK (instrumentation). |
| 6 | 12 | Three drift detectors (ADWIN/MMD/PSI); drift workers; drift home live; drift detail × 3. |
| 7 | 12 | Run comparison; Mode 2 (offline regression) end-to-end; bare-SDK example; finish TS SDK (eval defn + invariants). |
| 8 | 4–8 | README narrative + recorded walkthrough + final polish. |

**Realistic envelope:** 88–92h. ~13–19h of that is irreducibly human (video recording/editing, agent reality-check on real-ish data, drift calibration verification, spec/plan reviews and course-correction). The remaining ~70–75h is CC-augmented build time, where senior-level scaffolding goes ~5–10× faster than hand-written. Day 8 is a partial day for finishing artifacts; if days 1–7 stay on rails it's mostly polish.

**Risk-driven cut order** (if days 5–7 slip):

1. Drop bare-SDK example to a code skeleton + README walkthrough (saves ~3h).
2. Drop drift detail pages for tool-call and quality (keep input only) (saves ~2h).
3. Drop TS SDK regression tests, keep only type-check + 1 smoke test (saves ~2h).
4. Demote Mode 2 from "end-to-end UI" to "API + CLI script that produces a JSON report" (saves ~3h).

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Pydantic AI is new to user — multi-agent patterns may have edge cases | Time-box exploration on Day 1; fall back to bare Anthropic SDK for the planner+worker if Pydantic AI's multi-agent patterns are immature. |
| Drift not reliably visible in 7-day demo window | `scripts/seed_drift.py` produces synthetic time-windowed inputs designed to trigger each detector. Demo uses seeded data; README explains. |
| 84h envelope is tight | Cut order documented above. Each cut is reversible later without architecture changes. |
| LLM judge cost runs hot during development | Sample rate config on Mode 1; default to a cheap judge (Haiku) for online evals; reserve Sonnet/Opus for Mode 2. Cost ceiling enforced by `cost_within_budget` invariant. |
| OTel/GenAI conventions still evolving | Pin to a snapshot version; document the snapshot in the README; structure the exporter so a convention upgrade is a localized change. |

## Open questions for plan-time

- Embedding source for input drift: Anthropic embeddings (one less dep, requires a key for embedding calls) vs. local sentence-transformers (offline, adds a model file).
- Wire format for the ingestion endpoint: OTLP/HTTP+protobuf vs OTLP/HTTP+JSON. JSON is simpler to debug and inspect; protobuf is the standard. Likely JSON for dev simplicity.
- Whether to use `scikit-multiflow` (fewer LOC, adds a dep) or hand-roll ADWIN/Page-Hinkley (one fewer dep, ~150 LOC). Likely hand-roll for crispness and to demonstrate the math, with citations in comments.
- Chart library: `recharts` (default, well-known, accessible) vs `visx` (more control for the Gantt). Probably recharts for non-Gantt views and a hand-rolled SVG Gantt component.
- Workspace tooling: `uv` for Python, `pnpm` for TS — assumed unless they cause friction.

## What "done" looks like

- The repo at `https://github.com/<user>/agentaid` runs locally end-to-end with `make dev` (or equivalent), seeds drift, opens the UI, and walks through the demo.
- The README opens with a 5-minute video walkthrough and a one-paragraph thesis statement.
- A reviewer who skims for ten minutes can: identify the platform's distinctive opinion, see a typed SDK in two languages, watch the agent run, see drift fire, see eval scores regress on a comparison, and read clean source in at least one component.
- All four "irreducibly human" investments (video, reality check, drift calibration, plan reviews) have happened.

