"""Record a ~45s scripted UI tour of the AgentAid web app via Playwright.

Output: docs/walkthrough.mp4 (Playwright produces .webm; we transcode with ffmpeg).

Prereqs (one-time):
    uv add --dev playwright
    uv run playwright install chromium

The AgentAid server (port 8001 unless --port-api is set) and the Vite dev
server (port 5173) must both be running, with at least the seeded data
present (scripts/load_golden.py + scripts/seed_drift.py).

Usage:
    uv run python scripts/record_walkthrough.py
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path

from playwright.async_api import async_playwright

REPO = Path(__file__).resolve().parent.parent
WEB = "http://localhost:5173"
OUT_DIR = REPO / "tmp_recording"
FINAL_MP4 = REPO / "docs" / "walkthrough.mp4"
VIEWPORT = {"width": 1280, "height": 720}

# Concrete IDs we know exist in the seeded DB.
TRACE_ID = "seed-0080"          # late-epoch run with drift contribution
COMPARE_A = "seed-0001"         # high-quality epoch
COMPARE_B = "seed-0080"         # low-quality epoch (post-shift)


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
        # Cap page console noise from React Router warnings etc.
        page.on("pageerror", lambda exc: print(f"[pageerror] {exc}"))

        # 0–9 s — Drift home: three signals firing
        await page.goto(f"{WEB}/", wait_until="networkidle")
        await page.wait_for_timeout(2500)
        # Cursor pass over each drift card to draw the eye
        for sel in [
            "a:has-text('Input drift')",
            "a:has-text('Tool-call drift')",
            "a:has-text('Quality drift')",
        ]:
            try:
                await page.locator(sel).hover(timeout=2000)
                await page.wait_for_timeout(1500)
            except Exception:
                pass
        await page.wait_for_timeout(1500)

        # 9–20 s — Trace detail (Gantt) with a worker run
        await page.goto(f"{WEB}/runs/{TRACE_ID}", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        # Click a worker bar to surface span attributes
        try:
            bars = page.locator("[data-test='gantt-bar']")
            count = await bars.count()
            if count >= 2:
                await bars.nth(min(2, count - 1)).click(timeout=2000)
                await page.wait_for_timeout(2500)
        except Exception:
            pass
        await page.wait_for_timeout(3000)

        # 20–28 s — Drift detail (quality) — chart + threshold
        await page.goto(f"{WEB}/drift/quality", wait_until="networkidle")
        await page.wait_for_timeout(7000)

        # 28–39 s — Run comparison — scorecard + tool-call distribution
        await page.goto(
            f"{WEB}/compare?a={COMPARE_A}&b={COMPARE_B}",
            wait_until="networkidle",
        )
        await page.wait_for_timeout(5500)
        # Scroll to reveal tool-call distribution if it's below the fold
        try:
            await page.evaluate("window.scrollTo({ top: 200, behavior: 'smooth' })")
            await page.wait_for_timeout(2500)
            await page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' })")
            await page.wait_for_timeout(1500)
        except Exception:
            pass

        # 39–45 s — Eval results — four sparklines
        await page.goto(f"{WEB}/evals", wait_until="networkidle")
        await page.wait_for_timeout(4500)

        # Close to finalise the video file.
        await context.close()
        await browser.close()

    # Find the captured webm.
    webms = list(OUT_DIR.glob("*.webm"))
    if not webms:
        raise SystemExit("no recording produced")
    webm = max(webms, key=lambda p: p.stat().st_mtime)
    print(f"recorded {webm} ({webm.stat().st_size // 1024} KB)")

    # Transcode to MP4 (h264) for broad compatibility + smaller size.
    FINAL_MP4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(webm),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "23", "-preset", "medium",
        "-movflags", "+faststart",
        str(FINAL_MP4),
    ]
    subprocess.run(cmd, check=True)
    print(f"wrote {FINAL_MP4} ({FINAL_MP4.stat().st_size // 1024} KB)")

    # Clean up the temp dir.
    shutil.rmtree(OUT_DIR, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
