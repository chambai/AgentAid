export type RunStatus = "running" | "succeeded" | "failed";

export interface Run {
  id: string;
  agent_name: string;
  started_at: string;
  ended_at: string | null;
  status: RunStatus;
  prompt_sha: string | null;
  model: string | null;
  total_cost: number;
  total_tokens: number;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
}

export interface Span {
  id: string;
  run_id: string;
  parent_span_id: string | null;
  name: string;
  role: string | null;
  started_at: string;
  ended_at: string | null;
  attributes: Record<string, unknown>;
  events: Array<Record<string, unknown>>;
}

export interface RunDetail { run: Run; spans: Span[] }
export interface RunsList { runs: Run[] }

export type DriftSignal = "input" | "tool_call" | "quality";

export interface DriftState {
  signal: DriftSignal;
  detector_name: string;
  window: string;
  value: number;
  threshold: number;
  is_drifted: boolean;
  updated_at: string;
}

export type EvalMode = "online" | "regression" | "invariant";

export interface EvalResult {
  run_id: string;
  eval_name: string;
  mode: EvalMode;
  score: number;
  label: string | null;
  rationale: string | null;
  created_at: string;
}
