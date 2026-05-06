from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from agentaid.otel.exporter import AgentAidSpanExporter, _serialize_span
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import SpanContext, TraceFlags
from opentelemetry.trace.span import format_span_id, format_trace_id


def _make_readable_span() -> ReadableSpan:
    ctx = SpanContext(trace_id=0x12345678901234567890123456789012,
                      span_id=0xabcdef0123456789, is_remote=False,
                      trace_flags=TraceFlags(0x01))
    return ReadableSpan(
        name="planner.dispatch_worker",
        context=ctx,
        parent=None,
        attributes={"gen_ai.system": "anthropic", "gen_ai.request.model": "claude-haiku-4-5",
                    "agentaid.role": "planner", "agentaid.run_id": "run-001"},
        start_time=int(datetime(2026, 5, 6, 12, 0, 0).timestamp() * 1e9),
        end_time=int(datetime(2026, 5, 6, 12, 0, 1).timestamp() * 1e9),
    )

def test_serialize_span_emits_genai_attributes() -> None:
    span = _make_readable_span()
    payload = _serialize_span(span)
    assert payload["name"] == "planner.dispatch_worker"
    assert payload["attributes"]["gen_ai.system"] == "anthropic"
    assert payload["attributes"]["agentaid.role"] == "planner"
    assert payload["span_id"] == format_span_id(0xabcdef0123456789)
    assert payload["trace_id"] == format_trace_id(0x12345678901234567890123456789012)

@pytest.mark.asyncio
async def test_exporter_posts_to_endpoint() -> None:
    span = _make_readable_span()
    exporter = AgentAidSpanExporter(endpoint="http://localhost:8000/ingest")
    fake_response = type("R", (), {"status_code": 200})()
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=fake_response)) as p:
        result = exporter.export([span])
        await exporter._flush()
    assert result.name == "SUCCESS"
    p.assert_called()
    body = p.call_args.kwargs["json"]
    assert "spans" in body
    assert body["spans"][0]["attributes"]["gen_ai.system"] == "anthropic"
