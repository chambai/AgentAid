import type { RunDetail, RunsList, DriftState, EvalResult } from "./types";

const BASE = "/api";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`);
  return res.json() as Promise<T>;
}

export const api = {
  listRuns: (params: { limit?: number; offset?: number } = {}): Promise<RunsList> => {
    const q = new URLSearchParams();
    if (params.limit !== undefined) q.set("limit", String(params.limit));
    if (params.offset !== undefined) q.set("offset", String(params.offset));
    const qs = q.toString();
    return getJson<RunsList>(`/runs${qs ? `?${qs}` : ""}`);
  },
  getRun: (id: string): Promise<RunDetail> => getJson<RunDetail>(`/runs/${id}`),
  driftState: (): Promise<{ signals: DriftState[] }> =>
    getJson<{ signals: DriftState[] }>(`/drift`),
  driftSeries: (signal: "input" | "tool_call" | "quality"): Promise<{ points: DriftState[] }> =>
    getJson<{ points: DriftState[] }>(`/drift/series/${signal}`),
  evalsRecent: (params: { evalName?: string; limit?: number } = {}): Promise<{ results: EvalResult[] }> => {
    const q = new URLSearchParams();
    if (params.evalName) q.set("eval_name", params.evalName);
    if (params.limit !== undefined) q.set("limit", String(params.limit));
    const qs = q.toString();
    return getJson<{ results: EvalResult[] }>(`/evals/recent${qs ? `?${qs}` : ""}`);
  },
};
