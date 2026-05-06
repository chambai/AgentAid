# 5-minute walkthrough script

Run `uv run python scripts/run_demo.py` in a hidden terminal before recording.

| # | Time | Section | Action |
|---|---|---|---|
| 1 | 0:00–0:20 | **Hook** | "AgentAid is a drift-aware obs/eval platform for production agents — three signals other tools don't surface." |
| 2 | 0:20–1:05 | **Drift home** | Open `/`. Point at the three signal cards. Click `/drift/quality` — show time series + threshold. |
| 3 | 1:05–2:05 | **Trace detail** | Click a recent run. Walk the Gantt — planner span, parallel workers, tool calls. Click a slow span. Note attributes. |
| 4 | 2:05–2:45 | **Eval framework** | Open `/evals`. Four sparklines. Two LLM-judges, two invariants. |
| 5 | 2:45–3:45 | **Run comparison** | Open `/compare?a=…&b=…`. Walk scorecard. Highlight tool-call distribution shift. |
| 6 | 3:45–4:25 | **Framework-agnostic** | Terminal: run bare-Anthropic-SDK example. Refresh `/runs` — `bare-…` id appears. |
| 7 | 4:25–4:40 | **Close** | "Github at <url>; design + plan in `docs/superpowers/`." |

Upload to YouTube as **Unlisted**. Replace `https://youtu.be/PLACEHOLDER` in `README.md` with the real URL when done.
