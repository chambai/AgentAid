import { ExportResult, ExportResultCode } from "@opentelemetry/core";
import type { ReadableSpan, SpanExporter } from "@opentelemetry/sdk-trace-base";

interface SerializedSpan {
  trace_id: string;
  span_id: string;
  parent_span_id: string | null;
  name: string;
  kind: string;
  start_time_unix_nano: number;
  end_time_unix_nano: number;
  attributes: Record<string, unknown>;
  events: Array<{ name: string; timestamp_unix_nano: number; attributes: Record<string, unknown> }>;
  status: { code: string; description: string };
}

function _serialize(span: ReadableSpan): SerializedSpan {
  const ctx = span.spanContext();
  return {
    trace_id: ctx.traceId,
    span_id: ctx.spanId,
    parent_span_id: span.parentSpanId ?? null,
    name: span.name,
    kind: String(span.kind),
    start_time_unix_nano: span.startTime[0] * 1e9 + span.startTime[1],
    end_time_unix_nano: span.endTime[0] * 1e9 + span.endTime[1],
    attributes: { ...span.attributes },
    events: span.events.map(e => ({
      name: e.name,
      timestamp_unix_nano: e.time[0] * 1e9 + e.time[1],
      attributes: { ...(e.attributes ?? {}) },
    })),
    status: { code: String(span.status.code), description: span.status.message ?? "" },
  };
}

export class AgentAidSpanExporter implements SpanExporter {
  constructor(public endpoint = process.env.AGENTAID_ENDPOINT ?? "http://localhost:8000/ingest") {}

  export(spans: ReadableSpan[], cb: (result: ExportResult) => void): void {
    const payload = { spans: spans.map(_serialize) };
    fetch(this.endpoint, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(() => cb({ code: ExportResultCode.SUCCESS }))
      .catch((err) => cb({ code: ExportResultCode.FAILED, error: err as Error }));
  }

  async shutdown(): Promise<void> { /* fetch is fire-and-forget */ }
}
