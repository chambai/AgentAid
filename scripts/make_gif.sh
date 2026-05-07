#!/usr/bin/env bash
# Convert docs/walkthrough.mp4 (or a highlights edit) into a GitHub-friendly
# GIF using ffmpeg's two-pass palette workflow. Output: docs/walkthrough.gif.
#
# Usage:
#   bash scripts/make_gif.sh                           # uses docs/walkthrough.mp4
#   bash scripts/make_gif.sh path/to/highlights.mp4    # uses a custom source
#
# Notes:
#   - Lower fps + smaller width = smaller GIF. Defaults aim for ~5–10 MB on
#     a 60-second highlight; a full 5-minute walkthrough at these settings
#     can run 30+ MB which is poor on GitHub.
#   - For a tight portfolio hero, record or edit a 30–60 s highlight first.

set -euo pipefail

INPUT="${1:-docs/walkthrough.mp4}"
OUTPUT="docs/walkthrough.gif"
PALETTE="$(mktemp -t agentaid-palette-XXXXXX.png)"
trap 'rm -f "$PALETTE"' EXIT

FPS="${FPS:-12}"
WIDTH="${WIDTH:-900}"

if [ ! -f "$INPUT" ]; then
  echo "error: $INPUT not found"
  echo "record your walkthrough to that path first (or pass a different file)"
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "error: ffmpeg is not installed"
  exit 1
fi

echo "→ generating palette from $INPUT (fps=$FPS, width=$WIDTH)"
ffmpeg -y -loglevel error -i "$INPUT" \
  -vf "fps=$FPS,scale=$WIDTH:-1:flags=lanczos,palettegen=stats_mode=diff" \
  "$PALETTE"

echo "→ encoding GIF to $OUTPUT"
ffmpeg -y -loglevel error -i "$INPUT" -i "$PALETTE" \
  -lavfi "fps=$FPS,scale=$WIDTH:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5" \
  "$OUTPUT"

SIZE=$(du -h "$OUTPUT" | cut -f1)
echo "✓ done — $OUTPUT ($SIZE)"
echo
echo "tip: if the GIF is too large, lower FPS or WIDTH:"
echo "  FPS=10 WIDTH=720 bash scripts/make_gif.sh"
