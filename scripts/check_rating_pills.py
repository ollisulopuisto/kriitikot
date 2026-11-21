"""Real Chromium five-slot pill smoke, served from docs without scraping.
Run with Playwright installed and system Chrome available.
"""
import functools
import http.server
import os
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
output = Path(os.environ.get('SCREENSHOT_DIR', '/tmp/kriitikot-pill-check'))
output.mkdir(parents=True, exist_ok=True)
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass
server = http.server.ThreadingHTTPServer(
    ('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(root / 'docs')))
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=os.environ.get('CHROME_BIN', '/usr/bin/google-chrome-stable'),
            args=['--no-sandbox'])
        for width in (320, 390, 900, 1600):
            page = browser.new_page(viewport={'width': width, 'height': 900})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}/', wait_until='networkidle')
            page.wait_for_function('window.reviewWindow && window.currentMovieOffset >= 60')
            page.evaluate('document.fonts.ready')
            # Lazy renderer, every rating, linked and unlinked. Full width stars
            # must stay within both the colored face and the link target.
            page.evaluate('''() => {
                const fixture=document.createElement('div');fixture.id='rating-fixture';
                fixture.style='display:flex;flex-wrap:wrap;gap:12px;background:white;padding:20px';
                for(let n=1;n<=5;n++)for(const url of ['https://example.com/',''])
                    fixture.insertAdjacentHTML('beforeend', createReviewPill({rating_stars:n,source_url:url,source_publication:'hs'}));
                document.body.prepend(fixture);
            }''')
            assert page.locator('#rating-fixture .rating-pill').count() == 10
            geometry = page.locator('#rating-fixture .rating-pill').evaluate_all('''pills=>pills.map(p=>{
                const s=p.querySelector('.rating-stars'),r=s.getBoundingClientRect(),target=p.getBoundingClientRect();
                return {w:r.width,h:r.height,target:target.height,text:s.textContent.length,
                    slots:s.children.length,empty:s.querySelectorAll('.rating-star-empty').length,
                    ink:getComputedStyle(s).color,bg:getComputedStyle(s).backgroundImage,
                    fits:[...s.children].every(c=>{const b=c.getBoundingClientRect();return b.left>=r.left&&b.right<=r.right&&b.top>=r.top&&b.bottom<=r.bottom}),
                    inTarget:r.top>=target.top&&r.bottom<=target.bottom};
            })''')
            assert all(p['slots'] == 5 and p['empty'] == 5-p['text'] for p in geometry)
            assert all(p['fits'] and p['inTarget'] and p['ink'] == 'rgb(255, 255, 255)' for p in geometry)
            assert len({p['w'] for p in geometry}) == len({p['h'] for p in geometry}) == 1
            page.screenshot(path=str(output / f'scale-{width}.png'))
            page.locator('#rating-fixture').evaluate('e=>e.remove()')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
            page.screenshot(path=str(output / f'context-{width}.png'))
            page.locator('#windowing-toggle').click()
            page.evaluate('''() => {const s=document.querySelector('#star-filter-slider');s.value='4';window.filterByStars(4);window.reconcileFacetVisibility();}''')
            selector = '.movie-card .review-item' if width < 769 else 'tbody .rating-pill'
            counts = page.locator(selector).evaluate_all('''nodes=>nodes.filter(n=>n.checkVisibility({checkVisibilityCSS:true})&&n.getBoundingClientRect().height>0).map(n=>n.querySelector('.rating-stars')?.textContent.length).filter(Boolean)''')
            assert counts and all(n>=4 for n in counts), (width, counts)
            assert not errors, errors
            print(width, 'five-slot geometry, page width, and minimum-star filter passed')
            page.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
