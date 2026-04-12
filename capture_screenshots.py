#!/usr/bin/env python3
"""Capture full-page screenshots of the fireant dashboard pages."""

from playwright.sync_api import sync_playwright
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

URLS = [
    {
        "url": "https://josoyjjk-ui.github.io/fireant-dashboard/",
        "output": os.path.join(OUTPUT_DIR, "screenshot_main_dashboard.png"),
        "label": "Main Dashboard",
    },
    {
        "url": "https://josoyjjk-ui.github.io/fireant-dashboard/events/",
        "output": os.path.join(OUTPUT_DIR, "screenshot_events_page.png"),
        "label": "Events Page",
    },
]


def capture(page_cfg):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        print(f"[→] Navigating to {page_cfg['label']}: {page_cfg['url']}")
        page.goto(page_cfg["url"], wait_until="networkidle", timeout=30000)
        # Extra wait for any dynamic rendering (countdown timers, filters, etc.)
        page.wait_for_timeout(3000)

        print(f"[→] Capturing full-page screenshot → {page_cfg['output']}")
        page.screenshot(path=page_cfg["output"], full_page=True)

        file_size = os.path.getsize(page_cfg["output"])
        print(f"[✓] {page_cfg['label']} saved ({file_size:,} bytes)")

        browser.close()


if __name__ == "__main__":
    for cfg in URLS:
        capture(cfg)
    print("\n✅ All screenshots captured successfully.")
