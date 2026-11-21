"""H6 real-Chrome hover transitions, touch and accessibility regression."""
import functools
import http.server
import os
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('SCREENSHOT_DIR', '/tmp/kriitikot-h6-check'))
OUT.mkdir(parents=True, exist_ok=True)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


STATE = '''p=>{
    const face=p.querySelector('.rating-stars');
    const box=face.getBoundingClientRect(),cs=getComputedStyle(face);
    return {face:[box.x,box.y,box.width,box.height,cs.backgroundColor],
        stars:[...p.querySelectorAll('.rating-star')]
            .filter(n=>getComputedStyle(n).display!=='none').map(n=>{
                const paint=n.querySelector('.rating-star-paint');
                const shadow=n.querySelector('.rating-star-shadow');
                const b=paint.getBoundingClientRect();
                return {scale:b.width/n.getBoundingClientRect().width,
                    inside:b.left>=box.left && b.right<=box.right &&
                        b.top>=box.top && b.bottom<=box.bottom,
                    shadow:getComputedStyle(shadow).transform,
                    opacity:Number(getComputedStyle(shadow).opacity)};
            })};
}'''
server = http.server.ThreadingHTTPServer(
    ('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT / 'docs')))
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path='/usr/bin/google-chrome-stable',
            args=['--no-sandbox'])
        for touch in (os.environ.get('TOUCH') == '1',):
            for width in (int(os.environ.get('WIDTH', '390')),):
                page = browser.new_page(
                    viewport={'width': width, 'height': 900},
                    has_touch=touch, is_mobile=touch)
                page.goto(f'http://127.0.0.1:{server.server_port}',
                          wait_until='networkidle')
                page.wait_for_function('window.currentMovieOffset>=60')
                page.evaluate('window.reviewWindow.prepare()')
                selector = ('.movie-card .rating-pill' if width < 769 else
                            '#review-container-desktop td .rating-pill')
                host = page.locator(selector).first.evaluate_handle(
                    'n=>n.parentElement')
                for linked in (False, True):
                    for rating in range(1, 6):
                        pill = host.evaluate_handle('''(host,data)=>{
                            host.querySelector('.rating-pill').outerHTML=
                                createReviewPill(data);
                            return host.querySelector('.rating-pill');
                        }''', dict(rating_stars=rating,
                                  source_url='https://example.com/'
                                  if linked else '',
                                  source_publication='hs')).as_element()
                        page.mouse.move(0, 0)
                        pill.scroll_into_view_if_needed()
                        page.wait_for_timeout(550)
                        rest = pill.evaluate(STATE)
                        assert all(s['opacity'] == 0 for s in rest['stars'])
                        pill.hover()
                        page.wait_for_timeout(300)
                        raised = pill.evaluate(STATE)
                        assert raised['face'] == rest['face']
                        for before, after in zip(rest['stars'],
                                                 raised['stars']):
                            assert after['shadow'] == before['shadow']
                            assert after['inside']
                            assert abs(after['scale'] - (
                                1 if touch else 1.3)) < .01
                            assert abs(after['opacity'] - (
                                0 if touch else .28)) < .001
                        if not touch and width in (390, 1600) and linked:
                            page.screenshot(path=str(
                                OUT / f'h6-raised-{rating}-{width}.png'))
                        # Held hover does not loop or settle on a timer.
                        if rating == 5 and not touch:
                            page.wait_for_timeout(5100)
                            assert pill.evaluate(STATE) == raised
                        page.mouse.move(0, 0)
                        page.wait_for_timeout(550)
                        assert pill.evaluate(STATE) == rest, (
                            rating, linked, pill.evaluate(STATE), rest)
                        # Leaving during the rise must restore rest too.
                        pill.hover()
                        page.wait_for_timeout(70)
                        page.mouse.move(0, 0)
                        page.wait_for_timeout(550)
                        assert pill.evaluate(STATE) == rest, (
                            rating, linked, pill.evaluate(STATE), rest)
                        page.emulate_media(reduced_motion='reduce')
                        pill.hover()
                        page.wait_for_timeout(300)
                        assert pill.evaluate(STATE) == rest, (
                            rating, linked, pill.evaluate(STATE), rest)
                        page.emulate_media(reduced_motion='no-preference')
                print(width, 'touch' if touch else 'pointer',
                      'H6 entry/hold/exit/interruption/reduced-motion passed')
                page.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
