"""Record a scripted UI tour of AgentAid via Playwright.

Two surfaces in one tour:
    - Consumer UI (researcher reading) on http://localhost:5174
    - Platform UI (engineer monitoring) on http://localhost:5173

The recording lands at docs/walkthrough-uncaptioned.mp4. Captions and
architecture-layer frames are added by scripts/add_captions.py.

Prereqs (one-time):
    uv add --dev playwright
    uv run playwright install chromium

All three servers must be running with seeded data + at least one digest:
    AGENTAID_API_PORT=8001 make server   (port 8001)
    AGENTAID_API_PORT=8001 make web      (port 5173)
    AGENTAID_API_PORT=8001 make digest   (port 5174)
    uv run python scripts/load_golden.py
    uv run python scripts/seed_drift.py

Usage:
    uv run python scripts/record_walkthrough.py
"""
from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

from playwright.async_api import async_playwright

REPO = Path(__file__).resolve().parent.parent
PLATFORM_WEB = "http://localhost:5173"
CONSUMER_WEB = "http://localhost:5174"
OUT_DIR = REPO / "tmp_recording"
UNCAPTIONED_MP4 = REPO / "docs" / "walkthrough-uncaptioned.mp4"
VIEWPORT = {"width": 1280, "height": 720}

# Concrete IDs we know exist in the seeded DB / live runs.
DIGEST_RUN_ID = "live-f88779cec3"   # the live-agent run with a real 7 KB digest
TRACE_ID = "seed-0080"              # late-epoch run with drift contribution
COMPARE_A = "seed-0001"             # high-quality epoch
COMPARE_B = "seed-0080"             # low-quality epoch (post-shift)


async def main() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport=VIEWPORT,
            record_video_dir=str(OUT_DIR),
            record_video_size=VIEWPORT,
            device_scale_factor=1,
        )
        page = await context.new_page()
        page.on("pageerror", lambda exc: print(f"[pageerror] {exc}"))

        # ── Consumer surface (researcher) ─────────────────────────

        # 0–5 s — Digest list: cards of available research digests
        await page.goto(f"{CONSUMER_WEB}/", wait_until="networkidle")
        await page.wait_for_timeout(4500)

        # 5–11 s — Digest detail: rendered Markdown of the agent's output
        await page.goto(
            f"{CONSUMER_WEB}/digests/{DIGEST_RUN_ID}", wait_until="networkidle"
        )
        await page.wait_for_timeout(4000)
        # A small scroll to show the digest body is rich content, not a teaser
        try:
            await page.evaluate("window.scrollTo({ top: 220, behavior: 'smooth' })")
            await page.wait_for_timeout(1500)
        except Exception:
            pass

        # ── Platform surface (engineer) ────────────────────────────

        # 11–18 s — Drift home: three signals firing
        await page.goto(f"{PLATFORM_WEB}/", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        for sel in [
            "a:has-text('Input drift')",
            "a:has-text('Tool-call drift')",
            "a:has-text('Quality drift')",
        ]:
            try:
                await page.locator(sel).hover(timeout=1500)
                await page.wait_for_timeout(1200)
            except Exception:
                pass
        await page.wait_for_timeout(800)

        # 18–28 s — Trace detail (Gantt) with a click on a worker span
        await page.goto(f"{PLATFORM_WEB}/runs/{TRACE_ID}", wait_until="networkidle")
        await page.wait_for_timeout(2500)
        try:
            bars = page.locator("[data-test='gantt-bar']")
            count = await bars.count()
            if count >= 2:
                await bars.nth(min(2, count - 1)).click(timeout=2000)
                await page.wait_for_timeout(2500)
        except Exception:
            pass
        await page.wait_for_timeout(2000)

        # 28–34 s — Drift detail (quality) — chart with threshold
        await page.goto(f"{PLATFORM_WEB}/drift/quality", wait_until="networkidle")
        await page.wait_for_timeout(5500)

        # 34–43 s — Run comparison — scorecard + tool-call distribution shift
        await page.goto(
            f"{PLATFORM_WEB}/compare?a={COMPARE_A}&b={COMPARE_B}",
            wait_until="networkidle",
        )
        await page.wait_for_timeout(4500)
        try:
            await page.evaluate("window.scrollTo({ top: 200, behavior: 'smooth' })")
            await page.wait_for_timeout(2000)
            await page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' })")
            await page.wait_for_timeout(1500)
        except Exception:
            pass

        # 43–47 s — Eval results — four sparklines
        await page.goto(f"{PLATFORM_WEB}/evals", wait_until="networkidle")
        await page.wait_for_timeout(3500)

        # Close to finalise the video file.
        await context.close()
        await browser.close()

    # Find the captured webm and transcode straight into walkthrough-uncaptioned.mp4
    webms = list(OUT_DIR.glob("*.webm"))
    if not webms:
        raise SystemExit("no recording produced")
    webm = max(webms, key=lambda p: p.stat().st_mtime)
    print(f"recorded {webm} ({webm.stat().st_size // 1024} KB)")

    UNCAPTIONED_MP4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(webm),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-r", "30", "-crf", "23", "-preset", "medium",
        "-movflags", "+faststart",
        str(UNCAPTIONED_MP4),
    ]
    subprocess.run(cmd, check=True)
    print(f"wrote {UNCAPTIONED_MP4} ({UNCAPTIONED_MP4.stat().st_size // 1024} KB)")
    print("next: uv run python scripts/add_captions.py")

    shutil.rmtree(OUT_DIR, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
