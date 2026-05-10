# AgentAid

> An information searching tool and a drift-aware observability and evaluation platform for production AI agents.
> Beyond standard traces and metrics, it treats distribution shift across inputs, tool-call patterns, eval scores, and citation attribution as first-class monitoring signals. Application-agnostic and front-end independent.

![Walkthrough](docs/walkthrough.gif)

*Full-resolution recording: [`docs/walkthrough.mp4`](docs/walkthrough.mp4)*

![Drift home](docs/screenshots/01-drift-home.png)

Three first-class systems on top of an OpenTelemetry / GenAI ingestion layer:
trace storage with full run / span / tool-call detail; a typed eval framework
with three operating modes (online sampled, offline regression, trace
invariants) and four built-in templates; and four drift detectors —
**input** (MMD on query embeddings), **tool-call** (PSI on per-role tool
frequencies), **quality** (ADWIN on streaming judge scores), and
**attribution** (PSI on per-paper citation weights, a FADMON-style signal
adapted for closed-weight LLMs).

The bundled multi-agent arXiv research assistant (planner + worker, multi-modal
figure extraction) is the reference workload — exercising the platform on
real-shaped traffic and driving the walkthrough above.

**Stack:** Python · FastAPI · SQLModel async · Pydantic AI · Anthropic SDK ·
OpenTelemetry / GenAI · TypeScript · React 19 · Vite · TanStack Query · Recharts.

## Architecture

![Architecture](docs/diagrams/architecture.png)

Three layers, OTel/GenAI at the seam between them:

1. **Agent + SDK layer** — Pydantic AI reference agent and a bare-Anthropic-SDK
   example. Both emit OTel/GenAI spans via the `agentaid` Python or TypeScript SDK.
2. **Server layer** — FastAPI + SQLModel + SQLite. Ingests spans, runs LLM-judge
   evals async, runs four drift-detector workers on a 5-second tick.
3. **Frontend layer** — two Vite + React + TS apps: `agentaid-web` for the
   platform (engineers) and `arxiv-digest-web` for consumers (researchers).

## Future improvements

- **Retry + backoff + timeout on LLM calls.** Today the agent fails fast and
  surfaces the error in the UI; production-grade needs bounded retries and a
  hard timeout on `agent.run()`.
- **Embedding-based attribution** as a second-tier drift signal alongside
  citation-weight. Catches paraphrased grounding that the section-length proxy
  misses.
- **Surface judge rationale on Trace Detail.** `judge.py` returns it and the
  DB stores it, but the UI never shows the most interpretable LLM-as-Judge
  output.
- **Reflexion / in-loop self-critique.** Eval judges are post-hoc only today.
- **Pairwise / rank-based judging** for the run-comparison view, instead of
  absolute scores.
- **Production multi-tenant build-out** — edge agent + sanitised egress +
  per-tenant data plane (designed in
  [`docs/architecture/multi-tenant.md`](docs/architecture/multi-tenant.md)).
- **Real-time WebSocket trace streaming** instead of 5-second polling.
- **Additional drift methods** (KS, Wasserstein, page-level changepoint).
  Plugin interface already designed for this.

## More detail

Stakeholder split, architecture diagrams, design decisions, quick start,
screenshots, scope boundaries, multi-tenant roadmap, and repository layout
live in [`DETAILS.md`](DETAILS.md).

## License

MIT.
