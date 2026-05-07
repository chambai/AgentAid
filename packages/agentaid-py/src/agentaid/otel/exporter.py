from __future__ import annotations

import logging
from collections.abc import Sequence

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
    """OTel exporter that POSTs serialized spans to the AgentAid server.

    BatchSpanProcessor calls export() from a dedicated worker thread, so a
    synchronous HTTP client is correct here — it avoids the event-loop
    coordination issues that an async client would introduce when the host
    process is itself running asyncio (and would otherwise cause spans to
    be lost on process exit).
    """

    def __init__(
        self, endpoint: str = "http://localhost:8000/ingest", timeout: float = 5.0
    ) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if not spans:
            return SpanExportResult.SUCCESS
        payload = {"spans": [_serialize_span(s) for s in spans]}
        try:
            self._client.post(self.endpoint, json=payload)
            return SpanExportResult.SUCCESS
        except Exception:
            log.warning("agentaid exporter failed", exc_info=True)
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
