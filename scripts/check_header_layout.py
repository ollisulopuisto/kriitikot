"""Optional real-Chrome toolbar regression check and screenshot capture.
Run: uv run --with playwright python scripts/check_header_layout.py
Requires a local Chrome; override CHROME_BIN and SCREENSHOT_DIR if needed.
Does not scrape, regenerate docs, or change the database.
"""

import os
import subprocess
import tempfile
import time
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

root = str(Path(__file__).resolve().parents[1])
output = Path(os.environ.get("SCREENSHOT_DIR", "/tmp/kriitikot-captures"))
output.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryFile() as log:
    p = subprocess.Popen(
        [
            root + "/.venv/bin/python",
            "-m",
            "flask",
            "--app",
            "src/app",
            "run",
            "--port",
            "5432",
        ],
        cwd=root,
        env={**os.environ, "PYTHONPATH": root + "/src"},
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=os.environ.get(
                    "CHROME_BIN", "/usr/bin/google-chrome-stable"
                ),
                headless=True,
                args=["--no-sandbox"],
            )
            page = browser.new_page(
                viewport={"width": 1600, "height": 900}, device_scale_factor=1
            )
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            for _ in range(50):
                try:
                    page.goto("http://127.0.0.1:5432")
                    break
                except PlaywrightError:
                    time.sleep(0.1)
            page.locator(".desktop-filters").wait_for()
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(300)
            page.locator("#sort-movies-btn").click()
            page.locator("#sort-critics-btn").click()
            page.locator('.desktop-filters [data-publication="HS"]').click()
            assert page.locator("#reset-filters-desktop").is_visible()
            page.locator("#reset-filters-desktop").click()
            page.locator(".desktop-filters .toggle-label").click()
            assert page.locator("#favorites-toggle-desktop").is_checked()
            page.locator("#reset-filters-desktop").click()
            # Capture with active publication to show the reset button and active chip.
            page.locator('.desktop-filters [data-publication="HS"]').click()
            page.mouse.move(0, 0)
            page.wait_for_timeout(200)  # Let the active-chip colour transition finish.
            page.screenshot(path=str(output / "desktop.png"))
            print("desktop bar", page.locator(".desktop-filters").bounding_box())
            regions = {
                name: page.locator(".desktop-filters ." + name).bounding_box()
                for name in [
                    "sorting-group",
                    "group-favorites",
                    "group-reviews",
                    "group-stars",
                    "media-group",
                ]
            }
            assert regions["sorting-group"]["x"] == regions["group-favorites"]["x"]
            assert regions["group-reviews"]["x"] == regions["group-stars"]["x"]
            assert (
                regions["group-stars"]["y"]
                >= regions["group-reviews"]["y"] + regions["group-reviews"]["height"]
            )
            assert (
                regions["sorting-group"]["y"] + regions["sorting-group"]["height"]
                <= regions["group-favorites"]["y"]
            )
            assert regions["media-group"]["x"] > regions["group-stars"]["x"]
            assert page.locator("#sort-movies-btn").bounding_box()["height"] <= 40
            for width in [1100, 769]:
                page.set_viewport_size({"width": width, "height": 900})
                page.wait_for_timeout(100)
                for selector in [
                    ".sorting-group",
                    ".group-favorites",
                    ".group-stars",
                    ".group-reviews",
                    ".media-group",
                ]:
                    b = page.locator(".desktop-filters " + selector).bounding_box()
                    assert b["x"] >= 0 and b["x"] + b["width"] <= width, (
                        width,
                        selector,
                        b,
                    )
            for width in [390, 320]:
                page.set_viewport_size({"width": width, "height": 844})
                page.reload()
                page.locator("#mobile-filter-toggle").click()
                assert not page.locator(".desktop-filters").is_visible()
                for b in page.locator(".mobile-filter .media-filter-btn").all():
                    box = b.bounding_box()
                    assert (
                        box["height"] >= 44
                        and box["x"] >= 0
                        and box["x"] + box["width"] <= width
                    ), (width, box)
                page.locator("#reviews-plus-mobile").click()
                assert page.locator("#min-reviews-value-mobile").inner_text() == "2"
                page.locator("#stars-plus-mobile").click()
                assert page.locator("#star-filter-slider").input_value() == "2"
                page.locator('.mobile-filter [data-publication="HS"]').click()
                assert "active" in page.locator(
                    '.mobile-filter [data-publication="HS"]'
                ).get_attribute("class")
                page.locator("#favorites-toggle-mobile").check()
                assert page.locator("#favorites-toggle-desktop").is_checked()
                page.locator(".mobile-filters-container").evaluate("(e)=>e.scrollTop=0")
                page.evaluate("window.scrollTo(0,0)")
                page.wait_for_timeout(100)
                page.screenshot(path=str(output / f"mobile-{width}.png"))
                page.locator(".mobile-filters-container").evaluate(
                    "(e)=>e.scrollTop=e.scrollHeight"
                )
                assert page.locator(".mobile-filter .toggle-label").is_visible()
                print("mobile checked", width)
            assert not errors, errors
            browser.close()
    finally:
        p.terminate()
        p.wait()
