from __future__ import annotations
import asyncio
import logging
from typing import Sequence
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
    """OTel exporter that POSTs serialized spans to the AgentAid server."""
    def __init__(self, endpoint: str = "http://localhost:8000/ingest", timeout: float = 5.0) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)
        self._pending: list[asyncio.Task] = []

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        payload = {"spans": [_serialize_span(s) for s in spans]}
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        if loop.is_running():
            self._pending.append(loop.create_task(self._post(payload)))
        else:
            loop.run_until_complete(self._post(payload))
        return SpanExportResult.SUCCESS

    async def _post(self, payload: dict) -> None:
        try:
            await self._client.post(self.endpoint, json=payload)
        except Exception:
            log.warning("agentaid exporter failed", exc_info=True)

    async def _flush(self) -> None:
        if self._pending:
            await asyncio.gather(*self._pending, return_exceptions=True)
            self._pending.clear()

    def shutdown(self) -> None:
        try:
            asyncio.get_event_loop().run_until_complete(self._client.aclose())
        except Exception:
            pass
