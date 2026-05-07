import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow, parseISO } from "date-fns";
import { listDigests } from "../api/client";
import type { DigestSummary } from "../api/types";

function relativeTime(iso: string | null): string {
  if (!iso) return "";
  try {
    return formatDistanceToNow(parseISO(iso), { addSuffix: true });
  } catch {
    return iso;
  }
}

function dateWindow(from: string | null, to: string | null): string {
  if (from && to) return `${from} – ${to}`;
  if (from) return `from ${from}`;
  if (to) return `to ${to}`;
  return "";
}

function DigestCard({ d }: { d: DigestSummary }) {
  return (
    <Link to={`/digests/${d.run_id}`} className="digest-card">
      <p className="digest-card-interest">{d.research_interest ?? "Digest"}</p>
      {dateWindow(d.date_from, d.date_to) && (
        <p className="digest-card-date">{dateWindow(d.date_from, d.date_to)}</p>
      )}
      {d.top_paper_title && (
        <p className="digest-card-top-paper">{d.top_paper_title}</p>
      )}
      {d.generated_at && (
        <p className="digest-card-meta">Generated {relativeTime(d.generated_at)}</p>
      )}
    </Link>
  );
}

export default function DigestList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["digests"],
    queryFn: () => listDigests(),
  });

  if (isLoading) return <p className="status-msg">Loading digests…</p>;
  if (error) return <p className="error-msg">Failed to load digests: {String(error)}</p>;

  const digests = data?.digests ?? [];

  if (digests.length === 0) {
    return <p className="status-msg">No digests yet.</p>;
  }

  return (
    <ul className="digest-list">
      {digests.map((d) => (
        <li key={d.run_id}>
          <DigestCard d={d} />
        </li>
      ))}
    </ul>
  );
}
