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
