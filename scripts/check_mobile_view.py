"""Phone full-loaded view and responsive controls, no scrape/deployment.
Requires Playwright and Chrome. Serves the checked-in generated site.
"""
import functools
import http.server
import os
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
output = Path(os.environ.get('SCREENSHOT_DIR', '/tmp/kriitikot-mobile-view-check'))
output.mkdir(parents=True, exist_ok=True)
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
    functools.partial(QuietHandler, directory=str(root / 'docs')))
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get('CHROME_BIN', '/usr/bin/google-chrome-stable'), args=['--no-sandbox'])
        for width in (320, 390, 768):
            page = browser.new_page(viewport={'width': width, 'height': 844})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}', wait_until='networkidle')
            page.wait_for_function('window.reviewWindow && window.currentMovieOffset>=60')
            page.evaluate('document.fonts.ready')
            def full_phone():
                page.wait_for_function('!window.reviewWindow.enabled && window.reviewWindow.retainedCount===0')
                assert not page.locator('.windowing-controls').is_visible()
                assert not page.locator('#windowing-toggle').is_visible()
                assert not page.locator('#windowing-help').is_visible()
                assert page.locator('.window-spacer, .window-column-spacer').count() == 0
                assert page.locator('.movie-card').count() == page.evaluate('window.currentMovieOffset')
                assert page.locator('[aria-rowcount], [aria-colcount], [aria-rowindex], [aria-colindex]').count() == 0
            full_phone()
            page.screenshot(path=str(output / f'phone-{width}.png'))
            # Hidden controls must not steal sequential keyboard focus.
            page.keyboard.press('Tab')
            assert page.evaluate('document.activeElement?.id') != 'windowing-toggle'
            # An offscreen loaded card remains available to text search/readers.
            last = page.locator('.movie-card').last
            title = last.locator('.movie-card-title').inner_text()
            assert title and last.evaluate('n=>n.isConnected')
            # Keep scroll-ahead pagination even with card windowing disabled.
            page.wait_for_timeout(250)
            page.evaluate('window.scrollTo(0,document.documentElement.scrollHeight-innerHeight-50)')
            page.wait_for_function('window.currentMovieOffset>60')
            full_phone()
            assert last.evaluate('n=>n.isConnected')
            page.evaluate('window.filterByStars(4);document.querySelector("#star-filter-slider").value=4;window.reconcileFacetVisibility()')
            page.wait_for_timeout(160)
            full_phone()
            counts=page.locator('.movie-card .review-item').evaluate_all('nodes=>nodes.filter(n=>n.checkVisibility({checkVisibilityCSS:true})&&n.getBoundingClientRect().height>0).map(n=>n.querySelector(".rating-stars")?.textContent.length).filter(Boolean)')
            assert counts and min(counts)>=4
            page.evaluate('window.resetAllFilters()')
            page.wait_for_timeout(160)
            full_phone()
            # Save identity and state before desktop parks the same cards.
            page.evaluate('''() => {window.phoneOriginals=[...document.querySelectorAll('.movie-card')];window.phoneOriginals.forEach((n,i)=>n.testState={index:i});}''')
            # Phone -> desktop default -> phone -> desktop user full view.
            page.set_viewport_size({'width': 1200, 'height': 900})
            page.wait_for_function('window.reviewWindow.enabled')
            assert page.locator('#windowing-toggle').is_visible()
            assert page.locator('.window-spacer').count()>0
            assert page.locator('.movie-card').count()==0
            assert page.evaluate('window.phoneOriginals.every(n=>!n.isConnected)')
            # Desktop actually parked cards. Switching to phone must restore
            # the same original nodes before any full-view toggle can mask it.
            page.set_viewport_size({'width': width, 'height': 844})
            full_phone()
            assert page.evaluate("window.phoneOriginals.every((n,i)=>n.isConnected&&document.querySelectorAll('.movie-card')[i]===n&&n.testState.index===i)")
            page.set_viewport_size({'width': 1200, 'height': 900})
            page.wait_for_function('window.reviewWindow.enabled && window.reviewWindow.retainedCount>0')
            page.locator('#windowing-toggle').click()
            page.wait_for_function('!window.reviewWindow.enabled && window.reviewWindow.retainedCount===0')
            page.set_viewport_size({'width': width, 'height': 844})
            full_phone()
            page.set_viewport_size({'width': 1200, 'height': 900})
            page.wait_for_timeout(120)
            assert not page.evaluate('window.reviewWindow.enabled')
            assert page.locator('#windowing-toggle').get_attribute('aria-pressed') == 'true'
            assert not errors, errors
            print(width, 'phone controls hidden, loaded cards present, pagination/filter/reset and desktop preference passed')
            page.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
