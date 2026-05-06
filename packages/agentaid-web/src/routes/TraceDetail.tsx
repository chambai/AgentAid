import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import GanttChart, { type GanttSpan } from "../components/GanttChart";
import type { Span } from "../api/types";

function toGanttSpans(spans: Span[]): GanttSpan[] {
  if (spans.length === 0) return [];
  const t0 = Math.min(...spans.map(s => Date.parse(s.started_at)));
  return spans.map(s => {
    const start = Date.parse(s.started_at) - t0;
    const end = s.ended_at ? Date.parse(s.ended_at) - t0 : start;
    return {
      id: s.id, parentId: s.parent_span_id, name: s.name, role: s.role,
      start, end,
      durationLabel: `${((end - start) / 1000).toFixed(2)}s`,
    };
  });
}

export default function TraceDetail() {
  const { id = "" } = useParams();
  const [selected, setSelected] = useState<string | null>(null);
  const detail = useQuery({ queryKey: ["run", id], queryFn: () => api.getRun(id), enabled: Boolean(id) });

  if (detail.isLoading) return <div>Loading…</div>;
  if (detail.isError || !detail.data) return <div>Run not found.</div>;

  const { run, spans } = detail.data;
  const gantt = toGanttSpans(spans);
  const sel = spans.find(s => s.id === selected);

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <strong>{run.id}</strong> · {run.agent_name} · {run.status} · {run.total_tokens} tok · ${run.total_cost.toFixed(4)}
      </div>
      <div style={{ background: "#f7f7f7", padding: 8, marginBottom: 12, fontSize: 11, opacity: 0.85 }}>
        DRIFT CONTRIBUTION · (live in Task 23)
      </div>
      <GanttChart spans={gantt} onSpanClick={setSelected} highlightId={selected ?? undefined} />
      {sel && (
        <div style={{ marginTop: 16, padding: 12, border: "1px solid #ddd" }}>
          <div style={{ fontSize: 10, opacity: 0.7 }}>SELECTED · {sel.role ?? "—"} / {sel.name}</div>
          <pre style={{ background: "#f5f5f5", padding: 8, fontSize: 11, overflow: "auto" }}>
            {JSON.stringify(sel.attributes, null, 2)}
          </pre>
          {Boolean(sel.attributes["agentaid.figure_data_url"]) && (
            <img src={String(sel.attributes["agentaid.figure_data_url"])} alt="figure"
                 style={{ maxWidth: 600, marginTop: 8 }} />
          )}
        </div>
      )}
    </div>
  );
}
