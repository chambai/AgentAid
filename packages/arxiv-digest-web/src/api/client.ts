import type { DigestSummary, DigestDetail } from "./types";

const BASE = "/api";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`);
  return res.json() as Promise<T>;
}

export function listDigests(limit?: number): Promise<{ digests: DigestSummary[] }> {
  const q = limit !== undefined ? `?limit=${limit}` : "";
  return getJson<{ digests: DigestSummary[] }>(`/digests${q}`);
}

export function getDigest(id: string): Promise<DigestDetail> {
  return getJson<DigestDetail>(`/digests/${encodeURIComponent(id)}`);
}
