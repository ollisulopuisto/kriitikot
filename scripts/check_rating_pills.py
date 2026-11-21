"""Real Chromium five-slot pill smoke, served from docs without scraping.

Setup: install project requirements plus Playwright, BeautifulSoup4 and Jinja2
into the Python environment used to run this script. Install system Chrome or
set CHROME_BIN to its path. No scrape or deployment is performed.
"""

import functools
import http.server
import os
from pathlib import Path
import threading

try:
    from playwright.sync_api import sync_playwright
    from bs4 import BeautifulSoup
    from jinja2 import Environment, FileSystemLoader
except ImportError as error:
    raise SystemExit(
        "Rating smoke-check dependencies missing. Install project "
        "requirements plus playwright, beautifulsoup4 and jinja2 in this "
        "Python environment; Chrome is also required. Missing module: "
        + str(error.name)
    ) from error

root = Path(__file__).resolve().parents[1]
output = Path(os.environ.get("SCREENSHOT_DIR", "/tmp/kriitikot-pill-check"))
output.mkdir(parents=True, exist_ok=True)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


server = http.server.ThreadingHTTPServer(
    ("127.0.0.1", 0),
    functools.partial(QuietHandler, directory=str(root / "docs")),
)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=os.environ.get(
                "CHROME_BIN", "/usr/bin/google-chrome-stable"
            ),
            args=["--no-sandbox"],
        )
        for width in (320, 390, 900, 1600):
            page = browser.new_page(viewport={"width": width, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(
                f"http://127.0.0.1:{server.server_port}/",
                wait_until="networkidle",
            )
            page.wait_for_function(
                "window.reviewWindow && window.currentMovieOffset >= 60"
            )
            page.evaluate("document.fonts.ready")
            # Lazy renderer, every rating, linked and unlinked. Full width
            # stars
            # grow proportionally; five can overflow the face, never its tap
            # target.
            page.evaluate(("""
() => {
    const fixture = document.createElement('div');
    fixture.id = 'rating-fixture';
    fixture.style =
        'display:flex;flex-wrap:wrap;gap:12px;background:white;padding:20px';
    for (let n = 1; n <= 5; n++)
        for (const url of ['https://example.com/', ''])
            fixture.insertAdjacentHTML('beforeend',
                '<div class="review-item">' +
                createReviewPill({
                    rating_stars: n,
                    source_url: url,
                    source_publication: 'hs'
                }) + '</div>');
    document.body.prepend(fixture);
}
"""))
            assert page.locator("#rating-fixture .rating-pill").count() == 10
            measure = (root / "scripts/rating_pill_geometry.js").read_text(
                encoding="utf-8"
            )
            geometry = page.locator(
                "#rating-fixture .rating-pill"
            ).evaluate_all(measure)
            assert all(
                p["slots"] == 5 and p["empty"] == 5 - p["text"]
                for p in geometry
            )
            assert all(
                p["proportional"]
                and p["inTarget"]
                and p["ink"] == "rgb(255, 255, 255)"
                for p in geometry
            ), geometry
            assert [p["fs"] for p in geometry[::2]] == [
                12,
                14,
                17,
                22,
                29,
            ], geometry
            assert all(
                "34, 197, 94" in p["glow"] for p in geometry[-2:]
            ), geometry
            assert all(
                "34, 197, 94" not in p["faceShadow"] for p in geometry
            ), geometry
            if width < 769:
                assert all(p["target"] >= 44 for p in geometry), geometry
                actual_targets = page.locator(
                    ".movie-card a.rating-pill"
                ).evaluate_all(
                    ("""
nodes => nodes.filter(n => n.getBoundingClientRect()
    .height > 0).map(n => n.getBoundingClientRect()
    .height)
""")
                )
                assert (
                    actual_targets and min(actual_targets) >= 44
                ), actual_targets
            assert all(
                abs(p["w"] - 88) < 0.1 and abs(p["h"] - 17) < 0.1
                for p in geometry
            ), geometry
            # Negative controls: horizontal-only escape and the old face height
            # must
            # fail the same measurements, rather than only passing good CSS.
            broken = page.add_style_tag(
                content=(
                    "#rating-fixture .stars-5 .rating-star { posit"
                    "ion:relative; left:100px!important }"
                )
            )
            assert not all(
                p["inTarget"]
                for p in page.locator(
                    "#rating-fixture .rating-pill"
                ).evaluate_all(measure)
            )
            broken.evaluate("n=>n.remove()")
            old_face = page.add_style_tag(
                content=(
                    "#rating-fixture .rating-stars { "
                    "height:28.8px!important }"
                )
            )
            assert not all(
                abs(p["h"] - 17) < 0.1
                for p in page.locator(
                    "#rating-fixture .rating-pill"
                ).evaluate_all(measure)
            )
            old_face.evaluate("n=>n.remove()")
            clipping = page.add_style_tag(
                content=(
                    "#rating-fixture .rating-stars { "
                    "overflow:hidden!important }"
                )
            )
            assert not all(
                p["inTarget"]
                for p in page.locator(
                    "#rating-fixture .rating-pill"
                ).evaluate_all(measure)
            )
            clipping.evaluate("n=>n.remove()")
            slot_clip = page.add_style_tag(
                content=(
                    "#rating-fixture .rating-star { "
                    "overflow:hidden!important }"
                )
            )
            assert not all(
                p["inTarget"]
                for p in page.locator(
                    "#rating-fixture .rating-pill"
                ).evaluate_all(measure)
            )
            slot_clip.evaluate("n=>n.remove()")
            # Paint fits the border box but escapes the inner scrollport.
            border_pill = page.locator("#rating-fixture .stars-5").first
            border_pill.evaluate(("""
p => {
    const wrapper = document.createElement('div');
    wrapper.id = 'border-clip-control';
    wrapper.style =
        'border:20px solid black;width:96px;height:44px;overflow:hidden';
    p.before(wrapper);
    wrapper.append(p);
    p.style.transform = 'translateX(-10px)';
}
"""))
            assert not border_pill.evaluate(
                "(p,code)=>eval(code)([p])[0].inTarget", measure
            )
            border_pill.evaluate(("""
p => {
    const wrapper = p.parentElement;
    wrapper.before(p);
    p.style.transform = "";
    wrapper.remove()
}
"""))
            page.screenshot(path=str(output / f"scale-{width}.png"))
            page.locator("#rating-fixture").evaluate("e=>e.remove()")
            assert page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth"
            ), width
            # Mark origin using the actual server markup, not current order.
            from html.parser import HTMLParser

            class ServerCards(HTMLParser):
                titles = set()

                def handle_starttag(self, tag, attrs):
                    attrs = dict(attrs)
                    if attrs.get("class") == "movie-card":
                        self.titles.add(attrs["data-movie"])

            initial = ServerCards()
            initial.feed(
                (root / "docs/index.html").read_text(encoding="utf-8")
            )
            page.evaluate("window.reviewWindow.prepare()")
            # Ensure the lazy batch contains a five-star result too.
            page.evaluate("loadMoreMovies(movieTitles.length)")
            page.evaluate("window.reviewWindow.prepare()")
            container = (
                ".movie-card"
                if width < 769
                else "#review-container-desktop tbody tr"
            )
            page.locator(container).evaluate_all(
                ("""
(nodes, titles) => nodes.forEach(node => {
    const title = node.dataset.movie || node
        .querySelector(
            '.movie-title-main')?.textContent
        .trim();
    node.dataset.testOrigin = titles.includes(
            title) ?
        'server' : 'lazy';
})
"""),
                list(initial.titles),
            )
            check_ink = "(p,code)=>eval(code)([p])[0].inTarget"

            def check_page_pill(pill):
                pill.scroll_into_view_if_needed()
                assert pill.evaluate(check_ink, measure)
                saved = pill.evaluate("""p => {
                    const a=p.closest('.review-item')
                        || p.closest('.table-wrapper');
                    const old=a.getAttribute('style');
                    Object.assign(a.style, {minHeight:'0',height:'1px',
                        maxHeight:'1px',overflow:'hidden'});
                    return old;
                }""")
                assert not pill.evaluate(check_ink, measure)
                pill.evaluate(
                    """(p,old) => {
                    const a=p.closest('.review-item')
                        || p.closest('.table-wrapper');
                    if(old===null)a.removeAttribute('style');
                    else a.setAttribute('style',old);
                }""",
                    saved,
                )

            for origin in ("server", "lazy"):
                page.evaluate("window.reviewWindow.prepare()")
                candidates = page.locator(
                    container
                    + '[data-test-origin="'
                    + origin
                    + '"] '
                    + "a.rating-pill.stars-5"
                )
                assert candidates.count() > 0, (width, origin)
                sample = candidates.first
                sample.scroll_into_view_if_needed()
                assert sample.evaluate(check_ink, measure), (width, origin)
                # Exercise each template branch in place, never add a second
                # pill to a phone lane sized for one review.
                original_html = sample.evaluate("p=>p.outerHTML")
                original_count = (
                    sample.locator("..").locator(".rating-pill").count()
                )
                check_page_pill(sample)
                if origin == "server":
                    env = Environment(
                        loader=FileSystemLoader(root / "templates"),
                        autoescape=True,
                    )
                    env.filters["publication_name"] = str
                    review = dict(
                        rating_stars=5,
                        source_url="",
                        review_text="",
                        publication=dict(short_name="hs", name="HS"),
                    )
                    template = (
                        "_movie_card.html"
                        if width < 769
                        else "_movie_row.html"
                    )
                    html = env.get_template(template).render(
                        movie_title="Crown test",
                        critics_reviews={"Test critic": [review]},
                        all_critics=[dict(name="Test critic", id="test")],
                        poster_urls={},
                        letterboxd_urls={},
                        nytleffaan_urls={},
                        movie_review_counts={},
                        movie_rating_distributions={},
                    )
                    soup = BeautifulSoup(html, "html.parser")
                    unlinked_html = str(
                        soup.select_one("span.rating-pill.stars-5")
                    )
                    assert unlinked_html != "None"
                else:
                    unlinked_html = page.evaluate("""() => createReviewPill({
                        rating_stars:5, source_url:'', source_publication:'hs'
                    })""")
                # Keep the replacement element itself. A matching earlier
                # catalog record must never receive this check or restoration.
                unlinked = sample.evaluate_handle(
                    """(p,html) => {
                    const template=document.createElement('template');
                    template.innerHTML=html.trim();
                    const replacement=template.content.firstElementChild;
                    p.replaceWith(replacement);
                    return replacement;
                }""",
                    unlinked_html,
                ).as_element()
                assert unlinked is not None
                assert (
                    unlinked.evaluate(
                        "p=>p.parentElement.querySelectorAll('.rating-pill').length"
                    )
                    == original_count
                )
                # An earlier same-origin unlinked crown is a selection decoy.
                # Keep it outside the lane and ensure restoration ignores it.
                decoy = unlinked.evaluate_handle("""p => {
                    const decoy=p.cloneNode(true);
                    decoy.dataset.identityDecoy='true';
                    decoy.style.display='none';
                    p.before(decoy);
                    return decoy;
                }""").as_element()
                assert not unlinked.evaluate("(p,d)=>p===d", decoy)
                check_page_pill(unlinked)
                lane = unlinked.evaluate_handle("p=>p.parentElement")
                unlinked.evaluate("(p, html)=>p.outerHTML=html", original_html)
                assert lane.evaluate(
                    "(n,html)=>[...n.children].some(p=>p.outerHTML===html)",
                    original_html,
                )
                assert decoy.evaluate("p=>p.isConnected && p.tagName==='SPAN'")
                decoy.evaluate("p=>p.remove()")
            page.screenshot(path=str(output / f"context-{width}.png"))
            if width >= 769:
                page.locator("#windowing-toggle").check()
            page.evaluate(("""
() => {
    const s = document.querySelector(
        '#star-filter-slider');
    s.value = '4';
    window.filterByStars(4);
    window.reconcileFacetVisibility();
}
"""))
            selector = (
                ".movie-card .review-item"
                if width < 769
                else "tbody .rating-pill"
            )
            counts = page.locator(selector).evaluate_all(("""
nodes => nodes.filter(n => n.checkVisibility({
    checkVisibilityCSS: true
}) && n.getBoundingClientRect().height > 0).map(n => n
    .querySelector('.rating-stars')?.textContent
    .length).filter(Boolean)
"""))
            assert counts and all(n >= 4 for n in counts), (width, counts)
            assert not errors, errors
            print(
                width,
                "geometry, renderer-origin coverage and star filter passed",
            )
            page.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
