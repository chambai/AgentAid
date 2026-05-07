"""Burn time-range captions into docs/walkthrough.mp4.

Captions paraphrase the Action column of docs/RECORDING_SCRIPT.md, fitted
to the 42 s auto-recording's section breakdown.

Usage:  uv run python scripts/add_captions.py
Output: rewrites docs/walkthrough.mp4 in place; preserves the original
        as docs/walkthrough-uncaptioned.mp4 the first time it runs.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INPUT = REPO / "docs" / "walkthrough.mp4"
BACKUP = REPO / "docs" / "walkthrough-uncaptioned.mp4"
TMP = REPO / "docs" / ".walkthrough-captioned.mp4"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# (start_s, end_s, text). Times are seconds in the source video.
CAPTIONS: list[tuple[float, float, str]] = [
    (0.5,  8.5,  "Open /. Point at the three drift signal cards"),
    (9.0, 15.0,  "Walk the Gantt — planner span, parallel workers, tool calls"),
    (15.0, 20.0, "Click a span — surface its agentaid attributes"),
    (20.0, 27.5, "Drift detail — time series with threshold"),
    (28.0, 39.0, "Run comparison — scorecard + tool-call distribution shift"),
    (39.0, 42.5, "Eval results — four sparklines (two LLM-judges, two invariants)"),
]


def _escape(text: str) -> str:
    """Escape characters that drawtext treats specially.

    drawtext interprets these as filter-graph syntax: : , ' \\ % {}
    The safe pattern is: backslash-escape the bad ones.
    """
    out = text
    out = out.replace("\\", r"\\")
    out = out.replace(":", r"\:")
    out = out.replace(",", r"\,")
    out = out.replace("'", r"\'")
    out = out.replace("%", r"\%")
    return out


def build_filter() -> str:
    parts = []
    for start, end, text in CAPTIONS:
        parts.append(
            f"drawtext="
            f"fontfile={FONT}:"
            f"text='{_escape(text)}':"
            f"fontcolor=white:fontsize=22:"
            f"box=1:boxcolor=black@0.72:boxborderw=12:"
            f"x=(w-text_w)/2:y=h-text_h-28:"
            f"enable='between(t,{start},{end})'"
        )
    return ",".join(parts)


def main() -> None:
    if not INPUT.exists():
        raise SystemExit(f"error: {INPUT} not found")
    if not BACKUP.exists():
        print(f"→ backing up uncaptioned video to {BACKUP.relative_to(REPO)}")
        shutil.copy(INPUT, BACKUP)

    print(f"→ burning captions into {INPUT.relative_to(REPO)}")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(BACKUP),
        "-vf", build_filter(),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "23", "-preset", "medium",
        "-movflags", "+faststart",
        str(TMP),
    ]
    subprocess.run(cmd, check=True)
    TMP.replace(INPUT)

    size_kb = INPUT.stat().st_size // 1024
    print(f"✓ captioned {INPUT.relative_to(REPO)} ({size_kb} KB)")
    print(f"  uncaptioned backup at {BACKUP.relative_to(REPO)}")


if __name__ == "__main__":
    main()
