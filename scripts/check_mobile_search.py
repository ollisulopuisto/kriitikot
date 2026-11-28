"""Real Chrome mobile film search, generated docs, no scrape/deploy."""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(root / 'docs')))
Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for width in (320, 390, 768):
            page = browser.new_page(viewport={'width': width, 'height': 844})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}', wait_until='networkidle')
            search = page.locator('.mobile-film-search .film-search')
            assert search.is_visible()
            assert page.locator('.mobile-filter').evaluate('n=>n.classList.contains("collapsed")')
            assert search.bounding_box()['height'] >= 44
            assert search.evaluate('n=>parseFloat(getComputedStyle(n).fontSize)') >= 16
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.wait_for_function('window._cachedReviewsData')
            title = page.evaluate('Object.keys(window._cachedReviewsData).at(-1)')
            search.fill(title)
            page.wait_for_timeout(300)
            visible = page.locator('.movie-card').evaluate_all('ns=>ns.filter(n=>getComputedStyle(n).display!=="none").map(n=>n.dataset.movie)')
            assert visible == [title], visible
            assert search.evaluate('n=>n===document.activeElement')
            page.locator('#mobile-filter-toggle').click()
            assert search.is_visible()
            search.fill('zzzz-no-film-xyz')
            page.wait_for_timeout(300)
            assert page.locator('.movie-card').evaluate_all('ns=>ns.every(n=>getComputedStyle(n).display==="none")')
            search.fill('')
            page.wait_for_timeout(300)
            assert page.locator('.movie-card:visible').count() > 0
            page.evaluate('window.resetAllFilters()')
            assert search.input_value() == ''
            if width == 390:
                if not page.locator('.mobile-filter').evaluate('n=>n.classList.contains("collapsed")'):
                    page.locator('#mobile-filter-toggle').click()
                page.wait_for_timeout(350)
                page.screenshot(path='/downloads/kriitikot-mobile-search-built.png')
            page.set_viewport_size({'width': 1000, 'height': 844})
            assert not search.is_visible()
            assert page.locator('#review-container-desktop .film-search').is_visible()
            assert not errors, errors
            page.close()
        browser.close()
        print('Mobile search320/390/768: visible, tail/no-result/clear/reset/focus, breakpoint and no overflow pass')
finally:
    server.shutdown()
    server.server_close()
