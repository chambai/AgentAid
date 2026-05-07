"""Verify the redactor protocol + AllowlistRedactor default behavior.

Even though the redactor is wired up as a no-op by default in single-tenant
dev usage, the AllowlistRedactor is the load-bearing piece of the
multi-tenant story documented at docs/architecture/multi-tenant.md. These
tests pin its contract.
"""
from __future__ import annotations

from agentaid.otel.redactor import (
    AllowlistRedactor,
    NoOpRedactor,
    SpanRedactor,
)


def _span(**attrs) -> dict:
    return {
        "trace_id": "0" * 32,
        "span_id": "1" * 16,
        "parent_span_id": None,
        "name": "agent.run",
        "kind": "INTERNAL",
        "start_time_unix_nano": 0,
        "end_time_unix_nano": 1_000_000_000,
        "attributes": dict(attrs),
        "events": [],
        "status": {"code": "OK", "description": ""},
    }


def test_protocol_is_satisfied_by_both_implementations() -> None:
    assert isinstance(NoOpRedactor(), SpanRedactor)
    assert isinstance(AllowlistRedactor(), SpanRedactor)


def test_noop_passes_everything_through() -> None:
    span = _span(**{"agentaid.input": "secret prompt", "pii.email": "x@y.z"})
    out = NoOpRedactor().redact(span)
    assert out is not None
    assert out["attributes"]["agentaid.input"] == "secret prompt"
    assert out["attributes"]["pii.email"] == "x@y.z"


def test_allowlist_keeps_structural_metadata() -> None:
    span = _span(**{
        "agentaid.run_id": "live-abc",
        "agentaid.role": "planner",
        "agentaid.agent_name": "arxiv-planner",
        "gen_ai.system": "anthropic",
        "gen_ai.usage.input_tokens": 1234,
    })
    out = AllowlistRedactor().redact(span)
    assert out is not None
    kept = out["attributes"]
    assert kept["agentaid.run_id"] == "live-abc"
    assert kept["agentaid.role"] == "planner"
    assert kept["gen_ai.system"] == "anthropic"
    assert kept["gen_ai.usage.input_tokens"] == 1234


def test_allowlist_drops_content_attributes() -> None:
    span = _span(**{
        "agentaid.input": "what is concept drift?",
        "agentaid.output": '{"digest": "..."}',
        "agentaid.eval_result": "rationale text that should not leak",
    })
    out = AllowlistRedactor().redact(span)
    assert out is not None
    assert "agentaid.input" not in out["attributes"]
    assert "agentaid.output" not in out["attributes"]
    assert "agentaid.eval_result" not in out["attributes"]


def test_allowlist_drops_pii_and_confidential_prefixes() -> None:
    span = _span(**{
        "pii.email": "user@example.com",
        "pii.user_id": "u-123",
        "confidential.notes": "do not leak",
        "agentaid.run_id": "live-abc",
    })
    out = AllowlistRedactor().redact(span)
    assert out is not None
    assert out["attributes"] == {"agentaid.run_id": "live-abc"}


def test_allowlist_keeps_eval_score_carve_out() -> None:
    span = _span(**{
        "agentaid.eval.relevance_judge.score": 0.83,
        "agentaid.eval.relevance_judge.rationale": "off-topic claim text",
    })
    out = AllowlistRedactor().redact(span)
    assert out is not None
    kept = out["attributes"]
    assert kept["agentaid.eval.relevance_judge.score"] == 0.83
    assert "agentaid.eval.relevance_judge.rationale" not in kept


def test_allowlist_extra_allowlist_param() -> None:
    span = _span(**{"custom.metric": 42, "agentaid.input": "secret"})
    out = AllowlistRedactor(extra_allowlist={"custom.metric"}).redact(span)
    assert out is not None
    assert out["attributes"]["custom.metric"] == 42
    assert "agentaid.input" not in out["attributes"]


def test_allowlist_wipes_event_attributes() -> None:
    span = _span()
    span["events"] = [
        {"name": "step", "timestamp_unix_nano": 1, "attributes": {"prompt": "secret"}},
    ]
    out = AllowlistRedactor().redact(span)
    assert out is not None
    assert out["events"] == [
        {"name": "step", "timestamp_unix_nano": 1, "attributes": {}},
    ]
