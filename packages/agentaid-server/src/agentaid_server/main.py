from __future__ import annotations
import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db.engine import init_db
from .orchestrator.drift_workers import drift_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = None
    if os.getenv("AGENTAID_DRIFT_LOOP", "1") != "0":
        task = asyncio.create_task(drift_loop())
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

app = FastAPI(title="AgentAid", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

from .api import ingest as ingest_api
app.include_router(ingest_api.router)

from .api import runs as runs_api
app.include_router(runs_api.router)

from .api import drift as drift_api
app.include_router(drift_api.router)

from .api import evals as evals_api
app.include_router(evals_api.router)

from .api import datasets as datasets_api, regression as regression_api
app.include_router(datasets_api.router)
app.include_router(regression_api.router)

from .api import compare as compare_api
app.include_router(compare_api.router)

@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
