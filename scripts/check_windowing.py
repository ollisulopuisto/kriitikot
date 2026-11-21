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
  headers: [...document.querySelectorAll('#review-container-desktop thead th.rating-cell')].map(n=>[n.dataset.criticId,n.style.display,n.dataset.filtered||'']),
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
                    initial_y = pages[0].evaluate("window.scrollY")
                    max_y = min(p.evaluate("Math.max(0,document.documentElement.scrollHeight-innerHeight)") for p in pages)
                    for direction in [1, -1]:
                        if max_y > 0:
                            target = min(max(1, initial_y), max_y) if direction > 0 else min(initial_y, max_y - 1)
                            approach = max(0, target - height) if direction > 0 else min(max_y, target + height)
                            for p in pages:
                                p.evaluate("y=>window.scrollTo(0,y)", approach)
                            for p in pages:
                                p.wait_for_timeout(80)
                            for p in pages:
                                p.evaluate("y=>window.scrollTo(0,y)", target)
                            for p in pages:
                                p.wait_for_timeout(80)
                            before_margin, after_margin = (0.5, 1.5) if direction > 0 else (1.5, 0.5)
                        else:
                            # No scroll range. A delta-zero render is forward-biased.
                            pages[0].evaluate("window.reviewWindow.schedule()")
                            pages[0].wait_for_timeout(80)
                            before_margin, after_margin = 0.5, 1.5
                        # Inspect the actual mounted slice before MODEL restores it.
                        mounted = pages[0].evaluate(
                            """() => {const mobile=innerWidth<769;return [...document.querySelectorAll(mobile?'.movie-card':'#review-container-desktop tbody tr:not(.window-spacer)')].filter(n=>n.getBoundingClientRect().height>0).map(n=>({title:mobile?n.dataset.movie:n.querySelector('.movie-title-main')?.textContent,top:n.getBoundingClientRect().top,bottom:n.getBoundingClientRect().bottom,focused:n.contains(document.activeElement)}));}"""
                        )
                        logical = pages[1].evaluate(MODEL)
                        allowed = {
                            row[0]
                            for row in logical["cards" if width < 769 else "rows"]
                            if row[1] != "none"
                        }
                        assert all(
                            row["title"] in allowed for row in mounted
                        ), f"{label}: wrong filtered content mounted"
                        # Exact direction-specific overscan, independent of
                        # production margins(), in every filtered/sorted state.
                        bound = pages[1].evaluate(
                            """([before,after]) => {const mobile=innerWidth<769;return [...document.querySelectorAll(mobile?'.movie-card':'#review-container-desktop tbody tr')].filter(n=>{const r=n.getBoundingClientRect();return r.height>0&&r.bottom>=-innerHeight*before&&r.top<=innerHeight*(1+after);}).map(n=>mobile?n.dataset.movie:n.querySelector('.movie-title-main')?.textContent);}""",
                            [before_margin, after_margin],
                        )
                        bounded_titles = set(bound)
                        mounted_titles = {row["title"] for row in mounted}
                        assert len(mounted_titles) == len(mounted), f"{label}: duplicate mounted film"
                        assert bounded_titles <= mounted_titles, f"{label}: required overscan films missing"
                        assert all(
                            row["focused"] or row["title"] in bounded_titles
                            for row in mounted
                        ), f"{label}: filtered/sorted state retained off-window films"
                        assert len(mounted) <= len(bound) + sum(
                            row["focused"] for row in mounted
                        ), f"{label}: filtered/sorted mounting bound exceeded"
                        required = pages[1].evaluate(
                            """() => {const mobile=innerWidth<769;return [...document.querySelectorAll(mobile?'.movie-card':'#review-container-desktop tbody tr')].filter(n=>{const r=n.getBoundingClientRect();return r.height>0&&r.bottom>0&&r.top<innerHeight;}).map(n=>({title:mobile?n.dataset.movie:n.querySelector('.movie-title-main')?.textContent,top:n.getBoundingClientRect().top,bottom:n.getBoundingClientRect().bottom}));}"""
                        )
                        positions = {row["title"]: row for row in mounted}
                        for row in required:
                            assert (
                                row["title"] in positions
                            ), f"{label}: partly/fully visible result missing"
                            actual = positions[row["title"]]
                            assert (
                                actual["bottom"] > 0 and actual["top"] < height
                            ), f"{label}: viewport film mounted only in overscan"
                            assert (
                                abs(actual["top"] - row["top"]) < 3
                                and abs(actual["bottom"] - row["bottom"]) < 3
                            ), f"{label}: mounted result geometry differs from full view {actual} {row}"
                    models = [p.evaluate(MODEL) for p in pages]
                    if models[0] != models[1]:
                        (output / "mismatch.json").write_text(
                            json.dumps(models, ensure_ascii=False, indent=2)
                        )
                    assert (
                        models[0] == models[1]
                    ), f"{device}: windowed/full mismatch after {label}"
                    print(device, label, "same logical state", models[0]["offset"])

                expected_films = pages[0].evaluate(
                    "Object.keys(window._cachedReviewsData).length"
                )
                expected_reviews = pages[0].evaluate(
                    "Object.values(window._cachedReviewsData).flatMap(Object.values).flat().length"
                )
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
                for p in pages:
                    p.evaluate(
                        "window.resetAllFilters();document.getElementById('mobile-sort').click();document.querySelector('.mobile-filters-container [data-publication=DEMOKRAATTI]').click()"
                    )
                    p.wait_for_timeout(150)
                    before = p.evaluate(
                        "window.reviewWindow.prepare();[...document.querySelectorAll('.movie-card')].filter(c=>c.style.display!=='none').map(c=>c.dataset.movie)"
                    )
                    p.evaluate("window.loadMoreFacetAware()")
                    p.wait_for_timeout(150)
                    after = p.evaluate(
                        "window.reviewWindow.prepare();[...document.querySelectorAll('.movie-card')].filter(c=>c.style.display!=='none').map(c=>c.dataset.movie)"
                    )
                    assert set(before) <= set(
                        after
                    ), "sorted facet pagination hid revealed films"
                    assert len(after) == len(
                        set(after)
                    ), "pagination duplicated a visible film"
                    assert len(set(after)) > len(
                        set(before)
                    ), "sorted facet pagination revealed no distinct new films"
                    p.evaluate("window.resetAllFilters();window.loadMoreMovies(30)")
                same("sorted pagination")
                for p in pages:
                    p.evaluate(
                        "window.reviewWindow.prepare();const link=document.querySelector(innerWidth<769?'.movie-card a.rating-link':'tbody a.rating-link');link.focus();window.paginationFocus=link;window.loadMoreMovies(30)"
                    )
                    assert p.evaluate(
                        "document.activeElement===window.paginationFocus && window.paginationFocus.isConnected"
                    ), "sorted append lost focus"
                same("focused sorted pagination")
                for p in pages:
                    assert p.evaluate(
                        """() => {window.reviewWindow.prepare();const mobile=innerWidth<769;const direction=mobile?window.mobileMovieSortDirection:window.movieSortDirection;const titles=[...document.querySelectorAll(mobile?'.movie-card-title':'#review-container-desktop tbody .movie-title-main')].map(n=>n.textContent.trim());return !direction||titles.every((title,i)=>i===0||titles[i-1].localeCompare(title,'fi')*direction<=0);}"""
                    ), "pagination broke alphabetical order"
                full_page = pages[1]
                full_page.wait_for_timeout(100)
                assert (
                    full_page.locator(
                        "[aria-rowcount], [aria-colcount], [aria-rowindex], [aria-colindex]"
                    ).count()
                    == 0
                )
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
                    == expected_films
                )
                assert (
                    page.evaluate(
                        "Object.values(window._cachedReviewsData).flatMap(Object.values).flat().length"
                    )
                    == expected_reviews
                )
                assert (
                    page.evaluate(
                        'window.reviewWindow.prepare();[...document.querySelectorAll(".movie-card .review-item")].length'
                    )
                    == expected_reviews
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
                    == expected_films
                )
                # Create a real indexed pinned header in desktop mode before
                # printing, proving the assertion cannot pass on an absent clone.
                page.set_viewport_size({"width": 1600, "height": 900})
                page.evaluate("window.scrollTo(0,1000)")
                page.wait_for_timeout(150)
                page.evaluate("window.refreshStickyHeader()")
                page.wait_for_selector("#sticky-thead-clone [aria-colindex]")
                assert page.locator("#sticky-thead-clone").count() == 1
                page.evaluate("window.printPinned=document.getElementById('sticky-thead-clone')")
                page.evaluate('window.dispatchEvent(new Event("beforeprint"))')
                assert (
                    page.locator(
                        "#sticky-thead-clone [aria-colindex], #sticky-thead-clone [aria-rowindex]"
                    ).count()
                    == 0
                )
                assert page.locator(".movie-card").count() == expected_films
                page.emulate_media(media="print")
                assert page.evaluate("matchMedia('print').matches")
                assert page.locator(".window-spacer, .window-column-spacer").count() == 0
                assert page.locator(".windowing-controls").evaluate("n=>getComputedStyle(n).display") == "none"
                print_geometry = page.locator("#review-container-desktop tbody tr").evaluate_all(
                    "nodes=>nodes.map(n=>({height:n.getBoundingClientRect().height,cells:[...n.cells].filter(c=>!c.classList.contains('filler-column')).length,spacers:n.querySelectorAll('.window-column-spacer').length}))"
                )
                header_count = page.locator("#review-container-desktop thead th:not(.filler-column)").count()
                assert len(print_geometry) == expected_films
                assert all(row["height"] > 0 and row["cells"] == header_count and row["spacers"] == 0 for row in print_geometry), "print media did not lay out the complete review rows"
                assert page.locator("#review-container-desktop").evaluate("n=>getComputedStyle(n).display") != "none"
                print_cells = page.locator("#review-container-desktop tbody td:not(.filler-column)").evaluate_all(
                    "nodes=>nodes.map(n=>{const r=n.getBoundingClientRect(),h=document.querySelector('#review-container-desktop thead tr').cells[n.cellIndex];return (r.width>0&&r.height>0&&n.checkVisibility({checkOpacity:true,checkVisibilityCSS:true,contentVisibilityAuto:true}))||(!n.querySelector('.rating-pill')&&getComputedStyle(h).display==='none')})"
                )
                assert print_cells and all(print_cells), "print media hid logical review cells"
                print_ratings = page.locator("#review-container-desktop tbody .rating-pill").evaluate_all(
                    "nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return r.width>0&&r.height>0&&n.checkVisibility({checkOpacity:true,checkVisibilityCSS:true,contentVisibilityAuto:true})})"
                )
                assert len(print_ratings) == expected_reviews and all(print_ratings), "print media hid ratings"
                page.screenshot(path=str(output / f"{device}-print-media.png"))
                page.emulate_media(media="screen")
                assert not page.evaluate("matchMedia('print').matches")
                page.evaluate('window.dispatchEvent(new Event("afterprint"))')
                page.wait_for_function(
                    """() => {const clone=document.getElementById('sticky-thead-clone');const expected=[...document.querySelector('#review-container-desktop thead tr').cells].map(c=>c.getAttribute('aria-colindex'));return clone===window.printPinned&&expected.every((value,i)=>value!==null&&clone.tHead.rows[0].cells[i].getAttribute('aria-colindex')===value);}"""
                )
                full_page.evaluate("window.resetAllFilters()")
                full_page.wait_for_timeout(100)
                assert full_page.evaluate("window.reviewWindow.retainedCount") == 0
                print(device, "focus, bounds, print, breakpoint, data intact", count)
                for p in pages:
                    p.context.close()
            # Both native scrollbar-style scrolls and wheel navigation preload
            # downward only. A filter mutation alone must not append a batch.
            context = browser.new_context(viewport={"width": 1600, "height": 900})
            page = context.new_page()
            page.goto("http://127.0.0.1:5434")
            page.wait_for_function(
                "window.reviewWindow && window.currentMovieOffset>=60"
            )
            page.wait_for_timeout(300)
            page.evaluate(
                "window.reviewWindow.prepare();window.scrollTo(0,document.documentElement.scrollHeight-1800)"
            )
            page.wait_for_timeout(300)
            page.evaluate("window.scrollBy(0,-30)")
            page.wait_for_timeout(150)
            before_jump = page.evaluate("window.currentMovieOffset")
            page.evaluate("window.scrollBy(0,60)")
            page.wait_for_function(
                "(baseline) => window.currentMovieOffset>baseline", arg=before_jump
            )
            print(
                "scrollbar-compatible directional preload",
                page.evaluate("window.currentMovieOffset"),
            )
            stable = page.evaluate(
                "window.scrollTo(0,0);document.querySelector('.desktop-filters [data-publication=HS]').click();window.currentMovieOffset"
            )
            page.wait_for_timeout(500)
            page.wait_for_timeout(300)
            assert page.evaluate("window.currentMovieOffset") == stable
            context.close()
            context = browser.new_context(viewport={"width": 1600, "height": 900})
            page = context.new_page()
            page.goto("http://127.0.0.1:5434")
            page.wait_for_function(
                "window.reviewWindow && window.currentMovieOffset>=60"
            )
            page.locator("#sort-movies-btn").focus()
            page.evaluate(
                "window.reviewWindow.prepare();window.scrollTo(0,document.documentElement.scrollHeight-1800)"
            )
            page.wait_for_timeout(300)
            keyboard_before = page.evaluate("window.currentMovieOffset")
            page.keyboard.press("PageDown")
            page.wait_for_function(
                "(baseline) => window.currentMovieOffset>baseline", arg=keyboard_before
            )
            print(
                "keyboard pagination from focused toolbar",
                page.evaluate("window.currentMovieOffset"),
            )
            context.close()
            browser.close()
    finally:
        server.terminate()
        server.wait()
