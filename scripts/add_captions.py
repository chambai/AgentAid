"""Build the final walkthrough video.

Two stages:

1. Burn product-description captions over the uncaptioned UI tour. The
   captions describe what AgentAid *does* at each section (not how to use
   the UI).
2. Append three short architecture-layer frames at the end. Each crops one
   layer out of docs/diagrams/architecture.png, pads it to 1280x720, and
   overlays a two-line skill caption at the bottom — front-loading the
   technical surface a reviewer should be able to spot.

Usage:  uv run python scripts/add_captions.py
Output: rewrites docs/walkthrough.mp4 in place; preserves the original
        uncaptioned recording at docs/walkthrough-uncaptioned.mp4
        (gitignored) so the script is re-runnable without re-recording.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
INPUT = DOCS / "walkthrough.mp4"
BACKUP = DOCS / "walkthrough-uncaptioned.mp4"
FINAL = DOCS / "walkthrough.mp4"

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# (start_s, end_s, caption). Times are seconds in the source UI tour
# (docs/walkthrough-uncaptioned.mp4). Captions describe what AgentAid does at
# each section — the product surface, not the user's actions.
#
# The tour starts on the *consumer* surface (researcher reading the agent's
# output) and then crosses to the *platform* surface (engineer monitoring
# the agent), so the contrast between the two stakeholders lands first.
CAPTIONS: list[tuple[float, float, str]] = [
    # Consumer surface — researcher
    (0.5,   5.5,  "Search form — researchers initiate a digest by typing a research interest"),
    (6.5,  10.5,  "Existing digests are listed below — every prior agent run is one click away"),
    (11.5, 16.5,  "Each digest opens to the rendered Markdown — the agent's actual output for the customer"),
    # Platform surface — engineer
    (18.0, 23.5,  "Platform surface — AgentAid surfaces drift across inputs, tool-call patterns, and eval scores"),
    (24.5, 29.5,  "Multi-agent traces — planner spawns workers in parallel, every tool call instrumented"),
    (30.0, 34.0,  "Spans follow OpenTelemetry GenAI semantic conventions — framework-agnostic"),
    (34.5, 39.5,  "ADWIN online change detection on streaming eval scores, with adaptive thresholds"),
    (40.0, 48.5,  "Compare runs by score deltas, cost, and tool-call distribution shift (PSI)"),
    (49.0, 52.5,  "Eval-first orchestration — typed Pydantic results from LLM judges and invariants"),
]

# Each layer frame: a focused PUML render (rendered separately) + skill caption.
LAYER_FRAMES: list[dict] = [
    {
        "name": "agent-sdk",
        "image": DOCS / "diagrams" / "agent-sdk-layer.png",
        "line1": "Agent + SDK Layer  —  Pydantic AI multi-agent  ·  Anthropic SDK  ·  multi-modal vision",
        "line2": "OpenTelemetry GenAI instrumentation  ·  framework-agnostic via open conventions",
        "duration": 3.0,
    },
    {
        "name": "server",
        "image": DOCS / "diagrams" / "server-layer.png",
        "line1": "Server Layer  —  Python  ·  FastAPI  ·  SQLModel async  ·  OTel/GenAI ingestion",
        "line2": "Eval orchestrator (Mode 1 + 3)  ·  drift workers ADWIN / MMD / PSI  ·  Mode 2 regression",
        "duration": 3.0,
    },
    {
        "name": "frontend",
        "image": DOCS / "diagrams" / "frontend-layer.png",
        "line1": "Frontend Layer  —  TypeScript  ·  React 19  ·  Vite  ·  TanStack Query  ·  Recharts",
        "line2": "Drift-first information architecture  ·  typed REST client mirroring server schema",
        "duration": 3.0,
    },
]


def _write_textfile(text: str, path: Path) -> Path:
    """Write caption text to a file so drawtext can read via textfile= and
    bypass single-quote / colon / comma / apostrophe escaping rules. drawtext
    treats textfile contents as opaque text — no interpretation needed.
    """
    path.write_text(text, encoding="utf-8")
    return path


def _build_caption_filter(textfile_dir: Path) -> str:
    parts = []
    for i, (start, end, text) in enumerate(CAPTIONS):
        tf = _write_textfile(text, textfile_dir / f"caption_{i}.txt")
        parts.append(
            f"drawtext=fontfile={FONT_BOLD}:textfile={tf}:"
            f"fontcolor=white:fontsize=22:"
            f"box=1:boxcolor=black@0.72:boxborderw=12:"
            f"x=(w-text_w)/2:y=h-text_h-28:"
            f"enable='between(t,{start},{end})'"
        )
    return ",".join(parts)


def make_captioned_tour(out_path: Path, textfile_dir: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(BACKUP),
        "-vf", _build_caption_filter(textfile_dir),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-r", "30", "-crf", "23", "-preset", "medium",
        "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def make_layer_clip(layer: dict, out_path: Path, textfile_dir: Path) -> None:
    """Render a layer-focused PUML diagram (already a PNG) into a 1280x720
    frame: white background area for the diagram, 100 px black bar at the
    bottom carrying a two-line skill caption. Writes a `duration`-second
    30 fps MP4 clip.
    """
    image: Path = layer["image"]
    if not image.exists():
        raise SystemExit(f"error: {image} not found — render layer puml first")
    tf1 = _write_textfile(layer["line1"], textfile_dir / f"{layer['name']}_line1.txt")
    tf2 = _write_textfile(layer["line2"], textfile_dir / f"{layer['name']}_line2.txt")
    # Filter chain on the looped still image:
    #   1. scale to fit within 1240x600 keeping aspect
    #   2. pad to 1280x620 with white background, image centered
    #   3. extend bottom by 100 px black bar -> 1280x720
    #   4. drawtext line 1 (bold) + line 2 (regular) from textfiles
    vf = (
        f"scale=1240:600:force_original_aspect_ratio=decrease,"
        f"pad=1280:620:(1280-iw)/2:(620-ih)/2:white,"
        f"pad=1280:720:0:0:black,"
        f"drawtext=fontfile={FONT_BOLD}:textfile={tf1}:"
        f"fontcolor=white:fontsize=20:x=(w-text_w)/2:y=h-72,"
        f"drawtext=fontfile={FONT_REGULAR}:textfile={tf2}:"
        f"fontcolor=white:fontsize=18:x=(w-text_w)/2:y=h-38"
    )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-t", str(layer["duration"]),
        "-i", str(image),
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-r", "30", "-crf", "23", "-preset", "medium",
        "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def concat_clips(clips: list[Path], out_path: Path) -> None:
    """Concatenate clips that share resolution, fps, and pixel format."""
    inputs = []
    for c in clips:
        inputs += ["-i", str(c)]
    n = len(clips)
    streams = "".join(f"[{i}:v]" for i in range(n))
    filter_complex = f"{streams}concat=n={n}:v=1:a=0[outv]"
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-r", "30", "-crf", "23", "-preset", "medium",
        "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    if not BACKUP.exists():
        if INPUT.exists():
            print(f"→ backing up uncaptioned video to {BACKUP.relative_to(REPO)}")
            shutil.copy(INPUT, BACKUP)
        else:
            raise SystemExit(f"error: neither {INPUT} nor {BACKUP} exists; record first")

    for layer in LAYER_FRAMES:
        if not layer["image"].exists():
            raise SystemExit(
                f"error: {layer['image']} not found — render layer puml first via\n"
                f"  java -jar plantuml.jar -tpng docs/diagrams/{layer['name']}-layer.puml"
            )

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        textfile_dir = tmp / "captions"
        textfile_dir.mkdir()
        captioned = tmp / "captioned-tour.mp4"
        layer_clips: list[Path] = []

        print(f"→ burning captions into UI tour → {captioned.name}")
        make_captioned_tour(captioned, textfile_dir)

        for layer in LAYER_FRAMES:
            out = tmp / f"layer-{layer['name']}.mp4"
            print(f"→ rendering layer frame: {layer['name']}")
            make_layer_clip(layer, out, textfile_dir)
            layer_clips.append(out)

        print(f"→ concatenating {1 + len(layer_clips)} clips → {FINAL.relative_to(REPO)}")
        concat_clips([captioned, *layer_clips], FINAL)

    size_kb = FINAL.stat().st_size // 1024
    print(f"✓ wrote {FINAL.relative_to(REPO)} ({size_kb} KB)")


if __name__ == "__main__":
    main()
