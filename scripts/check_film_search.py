"""Chromium regressions for catalog search, no scrape or deployment."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from playwright.sync_api import sync_playwright
import os
root = Path(__file__).resolve().parents[1]
out = Path(os.environ.get('SCREENSHOT_DIR', '/tmp/kriitikot-search-check'))
out.mkdir(parents=True, exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(root / 'docs')))
Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('CHROME_BIN', '/usr/bin/google-chrome-stable'), args=['--no-sandbox'])
        for width in (900, 1600):
            page = browser.new_page(viewport={'width': width, 'height': 900})
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}', wait_until='networkidle')
            page.wait_for_function('window.currentMovieOffset>=60')
            title = page.evaluate('Object.keys(window._cachedReviewsData).at(-1)')
            # A tail-only exact query renders the matching tail, not all of it.
            page.locator('.film-search').fill(title)
            page.wait_for_timeout(250)
            assert page.locator('.movie-card').count() < 70
            visible = lambda: page.locator('.movie-card').evaluate_all('ns=>ns.filter(n=>n.style.display!=="none").map(n=>n.dataset.movie)')
            assert visible() == [title]
            page.locator('#sort-movies-btn').click()
            assert visible() == [title]
            shown_rows = page.locator('#review-container-desktop tbody tr').evaluate_all('ns=>ns.filter(n=>n.style.display!=="none").map(n=>n.querySelector(".movie-title-main")?.textContent.trim())')
            assert shown_rows == [title], shown_rows
            page.locator('#review-container-desktop tbody .movie-title-main', has_text=title).click()
            assert visible() == [title]
            assert page.locator('.film-search').first.input_value() == title
            # Editing the query clears movie-only selection without dropping facets.
            page.locator('.film-search').first.fill('')
            page.wait_for_timeout(250)
            assert page.locator('tbody tr[data-filtered="true"]').count() == 0
            page.evaluate('window.resetAllFilters()')
            assert page.evaluate('window.currentMovieOffset') == 60
            assert page.locator('.movie-card').count() == 60
            # Initial-batch selection must release both row and cell styles.
            search = page.locator('.film-search').first
            search.fill('Paper Tiger')
            page.wait_for_timeout(250)
            page.locator('tbody .movie-title-main', has_text='Paper Tiger').click()
            search.fill('Dry Leaf')
            page.wait_for_timeout(250)
            dry = page.locator('tbody tr').filter(
                has=page.locator('.movie-title-main', has_text='Dry Leaf'))
            def visible_ratings(row):
                return row.locator('.rating-pill').evaluate_all(
                    'ns=>ns.filter(n=>n.checkVisibility({checkVisibilityCSS:true})).length')
            assert dry.is_visible() and visible_ratings(dry) > 0
            # Negative control: the leaked row class must fail this oracle.
            dry.evaluate('n=>n.classList.add("dimmed")')
            assert visible_ratings(dry) == 0
            dry.evaluate('n=>n.classList.remove("dimmed")')
            search.fill('the')
            page.wait_for_timeout(250)
            page.locator('tbody .movie-title-main', has_text='The Magic Faraway Tree').click()
            search.fill('')
            page.wait_for_timeout(250)
            assert page.locator('tbody .selected, tbody .dimmed, tbody [data-filtered="true"]').count() == 0
            shown = page.locator('tbody tr').evaluate_all('ns=>ns.filter(n=>n.style.display!=="none" && n.querySelector(".rating-pill")).every(n=>[...n.querySelectorAll(".rating-pill")].some(p=>p.checkVisibility({checkVisibilityCSS:true})))')
            assert shown
            page.evaluate('window.resetAllFilters()')
            # Search through the actual pinned control without losing focus.
            page.evaluate('window.scrollTo(0,650)')
            pinned = page.locator('#sticky-thead-clone .film-search')
            pinned.wait_for()
            pinned.fill('Paper')
            page.wait_for_timeout(220)
            assert pinned.evaluate('n=>n===document.activeElement')
            pinned.press('End')
            pinned.press('Backspace')
            page.wait_for_timeout(220)
            assert pinned.input_value() == 'Pape'
            assert pinned.evaluate('n=>n===document.activeElement')
            page.wait_for_timeout(80)
            assert pinned.evaluate('n=>{const r=n.getBoundingClientRect(),f=document.querySelector(".desktop-filters").getBoundingClientRect();return r.top>=f.bottom && document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)===n}')
            pinned.fill('go')
            page.wait_for_timeout(250)
            def header_parity():
                return page.evaluate('''() => {
                    const cells=selector=>[...document.querySelectorAll(selector)].map(n=>[n.dataset.criticId,n.style.display,n.classList.contains('filter-hidden')]);
                    return JSON.stringify(cells('#review-container-desktop thead th.rating-cell'))===JSON.stringify(cells('#sticky-thead-clone th.rating-cell'));
                }''')
            assert header_parity()
            pinned.press('Tab')
            page.wait_for_timeout(100)
            if page.locator('#sticky-thead-clone').count():
                assert header_parity()
            else:
                assert page.locator('#review-container-desktop thead').evaluate('n=>n.style.visibility') == 'visible'
            page.screenshot(path=str(out / f'pinned-{width}.png'))
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.locator('#sticky-thead-wrapper').count() == 0
            assert page.locator('#review-container-desktop thead').evaluate('n=>n.style.visibility') == 'visible'
            assert not errors, errors
            page.close()
            print(width, 'sparse tail, sort, selection, reset, pinned focus, phone cleanup passed')
        page = browser.new_page(viewport={'width':1200,'height':900})
        page.goto(f'http://127.0.0.1:{server.server_port}', wait_until='networkidle')
        page.locator('.film-search').fill('a')
        page.wait_for_timeout(220)
        page.evaluate('''() => {window.rememberSliderWindow();const s=document.querySelector('#star-filter-slider');s.value=5;window.filterByStars(5);window.topUpSliderResults();}''')
        assert page.locator('.movie-card').count() < 100
        # Bounded DOM is not success if the matching review batch is short.
        completeness = page.evaluate('''() => {
            const state=currentFacetState();
            const total=movieTitles.reduce((count,title)=>count+
                (matchesFilmSearch(title)?Object.entries(allGroupedReviews[title])
                    .reduce((n,[critic,items])=>n+items.filter(review=>
                        reviewMatchesFacetState(review,critic,state)).length,0):0),0);
            return {loaded:loadedMatchingReviewCount(),total,
                wanted:facetRevealCount};
        }''')
        assert completeness['loaded'] >= min(completeness['total'], completeness['wanted']), completeness
        assert completeness['total'] > 0

        page.close()
        # Both a settled second query and a cleared query must invalidate all
        # pre-catalog windows, not just the currently active key.
        for clear_before_release in (False, True):
            page = browser.new_page(viewport={'width': 1200, 'height': 900})
            page.add_init_script('''const originalFetch=window.fetch;window.fetch=(url,...args)=>String(url).includes('reviews.json')?new Promise(resolve=>{window.releaseReviews=()=>resolve(originalFetch(url,...args));}):originalFetch(url,...args);''')
            page.goto(f'http://127.0.0.1:{server.server_port}', wait_until='domcontentloaded')
            page.locator('.film-search').fill('Anna minun rakastaa enemmän')
            page.wait_for_timeout(200)
            page.locator('.film-search').fill('One Battle After Another')
            page.wait_for_timeout(200)
            if clear_before_release:
                page.locator('.film-search').fill('')
                page.wait_for_timeout(200)
            page.evaluate('window.releaseReviews()')
            page.wait_for_function('window._cachedReviewsData')
            if clear_before_release:
                page.wait_for_function('window.currentMovieOffset===60')
            else:
                # One Battle After Another is outside the server batch and must appear without edits.
                page.wait_for_function('''[...document.querySelectorAll(
                    '.movie-card')].some(n=>n.dataset.movie==='One Battle After Another' &&
                        n.style.display!=='none')''')
            page.locator('.film-search').fill('Anna minun rakastaa enemmän')

            page.wait_for_function('window._cachedReviewsData && [...document.querySelectorAll(".movie-card")].some(n=>n.dataset.movie==="Anna minun rakastaa enemmän" && n.style.display!=="none")')
            page.locator('.film-search').fill('')
            page.wait_for_timeout(250)
            expected = 60 if clear_before_release else 30
            assert page.evaluate('window.currentMovieOffset') == expected
            assert page.locator('.movie-card').count() == expected
            page.close()
        print('delayed catalog query passed')
        browser.close()
finally:
    server.shutdown()
    server.server_close()
