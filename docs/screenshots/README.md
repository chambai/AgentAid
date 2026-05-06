# Screenshots

The README references six screenshots in this directory. Capture them by running the
app locally and using OS screenshot tooling.

Setup before capturing:

```bash
make server &      # in one terminal
make web &         # in another
uv run python scripts/load_golden.py
uv run python scripts/seed_drift.py
sleep 6            # let drift workers tick once
```

Then capture:

| File | URL | What to show |
|---|---|---|
| `01-drift-home.png` | `http://localhost:5173/` | All three drift signals — at least one in the "drifted" red state |
| `02-trace-gantt.png` | `http://localhost:5173/runs/<id>` | A planner+worker run with parallel worker spans visible |
| `03-run-comparison.png` | `http://localhost:5173/compare?a=<id1>&b=<id2>` | Two runs side-by-side, scorecard + tool distribution shift |
| `04-drift-detail.png` | `http://localhost:5173/drift/quality` | Time series chart with the threshold reference line |
| `05-eval-results.png` | `http://localhost:5173/evals` | Four sparklines for the four built-in evals |
| `06-architecture.png` | (hand-drawn) | System diagram. Use excalidraw, draw.io, or similar. Three layers (agent+SDK / server / frontend), with OTel/GenAI as the seam. |

PNG format, ~1600px wide max for reasonable file sizes.
