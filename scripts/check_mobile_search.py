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
            assert not search.is_visible()
            assert page.locator('.mobile-filter').evaluate('n=>n.classList.contains("collapsed")')
            page.locator('#mobile-filter-toggle').click()
            page.wait_for_timeout(350)
            assert search.is_visible()
            assert search.evaluate('n=>!!n.closest("#mobile-filters-content")')
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
            page.wait_for_timeout(350)
            assert not search.is_visible()
            page.locator('#mobile-filter-toggle').click()
            page.wait_for_timeout(350)
            assert search.is_visible()
            search.fill('Paper Tiger')
            page.wait_for_timeout(200)
            page.locator('#stars-plus-mobile').click()
            page.wait_for_timeout(100)
            page.locator('#mobile-filter-toggle').click()
            page.wait_for_timeout(350)
            assert page.locator('#mobile-filter-toggle').evaluate('n=>n.querySelector(".toggle-text").textContent+n.querySelector(".toggle-count").textContent') == 'Haku: paper tiger · +1'
            assert page.locator('.mobile-filter').evaluate('n=>n.classList.contains("has-active-filters")')
            assert page.locator('.mobile-filter-clear').is_visible()
            if width == 390:
                page.screenshot(path='/downloads/kriitikot-summary-active.png')
            # Long query stays on one line and remains available to screen readers.
            page.locator('#mobile-filter-toggle').click()
            page.wait_for_timeout(350)
            search.fill('pitkä elokuvahaku ' * 20)
            page.wait_for_timeout(200)
            page.locator('#mobile-filter-toggle').click()
            page.wait_for_timeout(350)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert page.locator('.toggle-text').evaluate('n=>n.scrollWidth>n.clientWidth')
            assert page.locator('.toggle-count').text_content() == ' · +1'
            assert page.locator('.toggle-count').evaluate('n=>n.scrollWidth<=n.clientWidth')
            if width in (320,390):
                page.screenshot(path=f'/downloads/kriitikot-summary-long-{width}.png')
            assert 'pitkä elokuvahaku' in page.locator('#mobile-filter-toggle').get_attribute('aria-label')
            clear=page.locator('.mobile-filter-clear')
            assert clear.evaluate('n=>!n.closest("#mobile-filter-toggle")')
            clear.focus()
            page.keyboard.press('Enter')
            page.wait_for_timeout(200)
            assert page.locator('.toggle-text').text_content() == 'Hakuehdot'
            assert search.input_value() == ''
            assert page.locator('.mobile-filter').evaluate('n=>n.classList.contains("collapsed")')
            page.locator('#mobile-filter-toggle').click()
            page.wait_for_timeout(350)
            page.locator('#stars-plus-mobile').click()
            page.locator('#mobile-filter-toggle').click()
            page.wait_for_timeout(100)
            assert page.locator('#mobile-filter-toggle').evaluate('n=>n.querySelector(".toggle-text").textContent+n.querySelector(".toggle-count").textContent') == 'Hakuehdot · 1'
            page.locator('.mobile-filter-clear').click()
            page.locator('#mobile-filter-toggle').click()
            page.wait_for_timeout(350)
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
                page.screenshot(path='/downloads/kriitikot-mobile-search-after-collapsed.png')
                page.locator('#mobile-filter-toggle').click()
                page.wait_for_timeout(350)
                page.screenshot(path='/downloads/kriitikot-mobile-search-after-expanded.png')
            page.set_viewport_size({'width': 1000, 'height': 844})
            assert not search.is_visible()
            assert page.locator('#review-container-desktop .film-search').is_visible()
            assert not errors, errors
            page.close()
        browser.close()
        print('Mobile search320/390/768: collapsed hidden, expanded visible, tail/no-result/clear/reset/focus, breakpoint and no overflow pass')
finally:
    server.shutdown()
    server.server_close()
