"""Real Chromium regression for connected-DOM windowing (no scraper/deploy).
Run with the project's Python environment plus playwright installed.
CHROME_BIN and SCREENSHOT_DIR may override the defaults.
"""

import os
import json
import subprocess
import tempfile
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
output = Path(os.environ.get("SCREENSHOT_DIR", "/tmp/kriitikot-windowing-check"))
output.mkdir(parents=True, exist_ok=True)

MODEL = """() => {
 window.reviewWindow.prepare();
 return {
  offset: window.currentMovieOffset,
  headers: [...document.querySelectorAll('thead th.rating-cell')].map(n=>[n.dataset.criticId,n.style.display,n.dataset.filtered||'']),
  rows: [...document.querySelectorAll('#review-container-desktop tbody tr')].map(n=>[n.querySelector('.movie-title-main')?.textContent,n.style.display,[...n.querySelectorAll('.rating-pill')].map(p=>[p.textContent.trim(),p.style.display])]),
  cards: [...document.querySelectorAll('.movie-card')].map(n=>[n.dataset.movie,n.style.display,[...n.querySelectorAll('.review-item')].map(r=>[r.dataset.critic,r.style.display])])
 };
}"""

with tempfile.TemporaryFile() as log:
    server = subprocess.Popen(
        [
            str(root / ".venv/bin/python"),
            "-m",
            "flask",
            "--app",
            "src/app",
            "run",
            "--port",
            "5434",
        ],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        time.sleep(0.8)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=os.environ.get(
                    "CHROME_BIN", "/usr/bin/google-chrome-stable"
                ),
                headless=True,
                args=["--no-sandbox"],
            )
            for device, width, height in [("desktop", 1600, 900), ("phone", 390, 844)]:
                pages = []
                errors = []
                for full in [False, True]:
                    context = browser.new_context(
                        viewport={"width": width, "height": height}
                    )
                    context.add_init_script("window.IntersectionObserver = undefined")
                    page = context.new_page()
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    page.goto("http://127.0.0.1:5434")
                    page.wait_for_function(
                        "window.reviewWindow && window._cachedReviewsData && window.currentMovieOffset >= 60"
                    )
                    page.evaluate("document.fonts.ready")
                    page.wait_for_timeout(150)
                    if full:
                        page.locator("#windowing-toggle").click()
                    pages.append(page)

                def same(label):
                    for p in pages:
                        p.wait_for_timeout(150)
                    models = [p.evaluate(MODEL) for p in pages]
                    if models[0] != models[1]:
                        (output / "mismatch.json").write_text(
                            json.dumps(models, ensure_ascii=False, indent=2)
                        )
                    assert (
                        models[0] == models[1]
                    ), f"{device}: windowed/full mismatch after {label}"
                    print(device, label, "same logical state", models[0]["offset"])

                same("initialization")
                actions = [
                    (
                        "publication",
                        (
                            "document.querySelector('.desktop-filters [data-publication=HS]').click()"
                            if width > 768
                            else "document.querySelector('.mobile-filters-container [data-publication=HS]').click()"
                        ),
                    ),
                    (
                        "stars",
                        "window.filterByStars(3);window.reconcileFacetVisibility()",
                    ),
                    ("reset", "window.resetAllFilters()"),
                    (
                        "favorite",
                        "window.toggleFavorite(document.querySelector('thead th.rating-cell').dataset.criticId)",
                    ),
                    ("favorites filter", "window.filterByFavorites(true)"),
                    ("reset again", "window.resetAllFilters()"),
                ]
                if width > 768:
                    actions += [
                        (
                            "movie sort",
                            "document.getElementById('sort-movies-btn').click()",
                        ),
                        (
                            "critic sort",
                            "document.getElementById('sort-critics-btn').click()",
                        ),
                        (
                            "critic",
                            "window.filterByCritic(document.querySelector('thead th.rating-cell'))",
                        ),
                        ("final reset", "window.resetAllFilters()"),
                    ]
                else:
                    actions += [
                        ("phone sort", "document.getElementById('mobile-sort').click()")
                    ]
                for label, js in actions:
                    for p in pages:
                        p.evaluate("window.scrollTo(0,1000)")
                        p.wait_for_timeout(60)
                        p.evaluate(js)
                    same(label)
                page = pages[0]
                page.evaluate(
                    "window.resetAllFilters();while(window.currentMovieOffset < Object.keys(window._cachedReviewsData).length)window.loadMoreMovies(30)"
                )
                page.wait_for_timeout(250)
                if width > 768:
                    page.evaluate(
                        'window.scrollTo(0,4000);document.querySelector(".table-wrapper").scrollLeft=2500'
                    )
                    page.wait_for_timeout(120)
                    # Each mounted critic cell still aligns with its logical header, including
                    # after hidden columns and colspan spacer groups.
                    offsets = page.evaluate(
                        """() => [...document.querySelectorAll('tbody tr:not(.window-spacer) td.rating-cell')].filter(c=>c.getBoundingClientRect().width>0).map(c=>{const h=document.querySelector('thead tr').cells[Number(c.getAttribute('aria-colindex'))-1];return Math.abs(c.getBoundingClientRect().left-h.getBoundingClientRect().left);})"""
                    )
                    if not offsets or max(offsets) >= 1.1:
                        page.screenshot(path=str(output / "alignment-error.png"))
                        print(
                            page.evaluate(
                                """() => [...document.querySelector('tbody tr:not(.window-spacer)').cells].map(c=>({idx:c.getAttribute('aria-colindex'),span:c.colSpan,x:c.getBoundingClientRect().left,w:c.getBoundingClientRect().width,head:c.getAttribute('aria-colindex')?document.querySelector('thead tr').cells[Number(c.getAttribute('aria-colindex'))-1]?.getBoundingClientRect().left:null,text:c.textContent.slice(0,20)}))"""
                            )
                        )
                    assert (
                        offsets and max(offsets) < 1.1
                    ), f"column alignment {max(offsets)}"
                    focus = page.locator(
                        "tbody tr:not(.window-spacer) a.rating-link"
                    ).first
                else:
                    page.evaluate("window.scrollTo(0,4000)")
                    page.wait_for_timeout(100)
                    focus = page.locator(".movie-card a.rating-link").first
                focus.focus()
                page.evaluate("window.savedFocus=document.activeElement")
                page.evaluate("window.scrollBy(0,4000)")
                page.wait_for_timeout(100)
                assert page.evaluate(
                    "document.activeElement===window.savedFocus && window.savedFocus.isConnected"
                ), "scroll lost focus"
                page.keyboard.press("Tab")
                page.wait_for_timeout(80)
                assert page.evaluate(
                    "document.activeElement!==document.body"
                ), "Tab lost focus"
                page.screenshot(path=str(output / f"{device}-scrolled.png"))
                count = (
                    page.locator("tbody td").count()
                    if width > 768
                    else page.locator(".movie-card").count()
                )
                assert count < (
                    2500 if width > 768 else 20
                ), f"unbounded connected DOM {count}"
                assert (
                    page.evaluate(
                        'window.reviewWindow.prepare();document.querySelectorAll(".movie-card").length'
                    )
                    == 312
                )
                assert (
                    page.evaluate(
                        "Object.values(window._cachedReviewsData).flatMap(Object.values).flat().length"
                    )
                    == 1072
                )
                assert not errors, errors
                # A breakpoint change restores the logical collection before remeasuring.
                page.set_viewport_size(
                    {"width": 390 if width > 768 else 1600, "height": height}
                )
                page.wait_for_timeout(180)
                assert (
                    page.evaluate(
                        'window.reviewWindow.prepare();document.querySelectorAll(".movie-card").length'
                    )
                    == 312
                )
                page.evaluate('window.dispatchEvent(new Event("beforeprint"))')
                assert page.locator(".movie-card").count() == 312
                page.evaluate('window.dispatchEvent(new Event("afterprint"))')
                print(device, "focus, bounds, print, breakpoint, data intact", count)
                for p in pages:
                    p.context.close()
            # Automatic pagination requires actual scrolling intent, not a filter's
            # layout shrink or a programmatic scroll into the sentinel's preload area.
            context = browser.new_context(viewport={"width": 1600, "height": 900})
            page = context.new_page()
            page.goto("http://127.0.0.1:5434")
            page.wait_for_function(
                "window.reviewWindow && window.currentMovieOffset>=60"
            )
            page.evaluate(
                "window.scrollTo(0,document.documentElement.scrollHeight-1800)"
            )
            page.wait_for_timeout(200)
            assert page.evaluate("window.currentMovieOffset") == 60
            page.mouse.wheel(0, 300)
            page.wait_for_function("window.currentMovieOffset>60")
            print(
                "directional boundary preload",
                page.evaluate("window.currentMovieOffset"),
            )
            context.close()
            browser.close()
    finally:
        server.terminate()
        server.wait()
