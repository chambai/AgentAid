# AgentAid

> A drift-aware observability and evaluation platform for production AI agents,
> built around the thesis that distribution drift — on agent inputs, tool-call
> patterns, and eval scores — is a first-class signal that traces and metrics
> alone don't surface.

[▶ 5-minute walkthrough video](https://youtu.be/PLACEHOLDER) <!-- linked in Task 32 once recorded -->

![Drift home](docs/screenshots/01-drift-home.png)

## What this is

AgentAid ingests OpenTelemetry traces using the GenAI semantic conventions
(`gen_ai.*` and `agentaid.*` attributes) and runs three first-class systems on top:

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

Three layers, OTel/GenAI at the seam between them:

1. **Agent + SDK layer** — Pydantic AI reference agent and a bare-Anthropic-SDK
   example. Both emit OTel/GenAI spans via the `agentaid` Python or TypeScript SDK.
2. **Server layer** — FastAPI + SQLModel + SQLite. Ingests spans, runs LLM-judge
   evals async, runs three drift-detector workers on a 5-second tick.
3. **Frontend layer** — Vite + React + TypeScript. Drift-first home, Gantt trace
   detail, summary-led run comparison, drift detail × 3, eval results, datasets.

## Why these choices

- **OTel + GenAI conventions** instead of a vendor format → reusable on any agent
  stack; the bare-SDK example proves it.
- **Pydantic AI** for the reference agent → typed end-to-end, async-native, thin
  enough to debug into and instrument cleanly.
- **Hand-rolled ADWIN/MMD/PSI** instead of `scikit-multiflow` → the math is
  visible and the dependency footprint stays small.
- **Eval-first orchestration** → eval results are first-class typed objects;
  drift detectors subscribe to eval streams, so quality drift is wired to the
  same numbers a developer reasons about.
- **Polyglot SDK** (Python + TypeScript) → demonstrates parity in the platform's
  contract; both speak the same OTel/GenAI wire format.

## Quick start

```bash
make install
make server   # http://localhost:8000
make web      # http://localhost:5173
uv run python scripts/load_golden.py
uv run python scripts/seed_drift.py   # makes drift visibly fire in the demo
```

Run the reference agent end-to-end against the AgentAid server:

```bash
AGENTAID_ENDPOINT=http://localhost:8000/ingest uv run python -m arxiv_agent
```

Run the bare-Anthropic-SDK example through the same ingestion pipeline:

```bash
AGENTAID_ENDPOINT=http://localhost:8000/ingest uv run python -m bare_sdk_example.example
```

Run a Mode 2 offline regression against the golden dataset:

```bash
curl -sS -X POST http://localhost:8000/regressions \
  -H 'content-type: application/json' \
  -d '{"dataset_id":"golden-arxiv-v1","prompt_sha":"HEAD","model":"claude-sonnet-4-6"}'
```

Then open `/datasets` to watch results stream in.

## Screenshots

| Drift home | Trace detail (Gantt) | Run comparison |
|---|---|---|
| ![home](docs/screenshots/01-drift-home.png) | ![gantt](docs/screenshots/02-trace-gantt.png) | ![compare](docs/screenshots/03-run-comparison.png) |

## Out of scope (deliberate)

| Out | Why |
|---|---|
| Multi-tenancy / auth | Single-developer dev tool. |
| Real-time WebSocket streaming | Polling is sufficient for the demo. |
| Drift methods beyond ADWIN/MMD/PSI | Plugin interface designed for additions; demonstrating the interface matters more than method count. |
| Mobile-responsive UI | Reviewer is on a desktop. |
| Live deployment | Replaced by the recorded walkthrough above. |
| Prompt-versioning UI | Prompts are code, versioned in git, surfaced as SHAs. UI for editing them is low ROI. |
| OpenAI provider | Anthropic-only; OTel/GenAI conventions and the bare-SDK example carry the framework-agnostic claim. |

## Repository layout

```
agentaid/
├── packages/
│   ├── agentaid-py/         # Python SDK: otel exporter, eval framework, drift detectors
│   ├── agentaid-ts/         # TypeScript SDK: otel exporter, eval define, invariants
│   ├── agentaid-server/     # FastAPI server: ingestion, evals, drift workers, regression
│   ├── agentaid-web/        # Vite + React + TS frontend
│   ├── reference-agent/     # Pydantic AI arXiv agent + mock arXiv layer
│   └── bare-sdk-example/    # Bare Anthropic SDK + manual otel — framework-agnostic proof
├── eval/golden/             # 10-row curated dataset for Mode 2 regression
├── scripts/
│   ├── load_golden.py       # Seeds golden dataset into the server
│   ├── seed_drift.py        # Synthetic drift seed for demos
│   └── run_demo.py          # Scripted demo driver
└── docs/superpowers/        # Design spec + implementation plan
```

See `docs/superpowers/specs/2026-05-06-agentaid-design.md` for the full design,
and `docs/superpowers/plans/2026-05-06-agentaid-implementation.md` for the plan
that produced this implementation.

## License

MIT.
