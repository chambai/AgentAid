from __future__ import annotations
from datetime import datetime
from typing import Any
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON

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
