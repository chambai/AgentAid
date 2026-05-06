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

from .api import ingest as ingest_api
app.include_router(ingest_api.router)

from .api import runs as runs_api
app.include_router(runs_api.router)

from .api import drift as drift_api
app.include_router(drift_api.router)

@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
