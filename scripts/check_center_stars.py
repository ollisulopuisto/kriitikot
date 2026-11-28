"""Real touch-Chrome check, local docs only, no scrape/deploy."""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from playwright.sync_api import sync_playwright
from pathlib import Path
root = Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(root/'docs')))
Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for width in (320, 390, 768):
            page = browser.new_page(viewport={'width': width, 'height': 844}, is_mobile=True, has_touch=True)
            errors=[]
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}', wait_until='networkidle')
            row = page.locator('.review-item').filter(has=page.locator('.rating-pill')).first
            row.evaluate('n=>window.scrollBy(0,n.getBoundingClientRect().top+n.getBoundingClientRect().height/2-innerHeight/2)')
            # Stop future scroll events while taking before/after, then explicitly settle.
            page.evaluate('window.dispatchEvent(new Event("touchstart"))')
            before=row.bounding_box()
            href=row.locator('a.rating-pill').get_attribute('href')
            if width==390:page.screenshot(path='/downloads/kriitikot-stars-before.png')
            page.evaluate('window.dispatchEvent(new Event("touchend"))')
            page.wait_for_function('document.querySelectorAll(".center-star-active").length===1', timeout=2000)
            page.wait_for_timeout(280)  # let the lift paint within its 800ms window
            assert page.locator('.center-star-active').count()==1
            assert row.get_attribute('class').find('center-star-active')>=0
            transform=row.locator('.rating-star-paint').first.evaluate('n=>getComputedStyle(n).transform')
            assert transform!='none' and transform!='matrix(1, 0, 0, 1, 0, 0)',transform
            assert row.bounding_box()==before
            assert row.locator('a.rating-pill').get_attribute('href')==href
            if width==390:page.screenshot(path='/downloads/kriitikot-stars-active.png')
            page.wait_for_timeout(700)
            page.evaluate('window.dispatchEvent(new Event("scroll"))')
            page.wait_for_timeout(300)
            assert page.locator('.center-star-active').count()==0
            # A fresh visit with reduced motion must stay static.
            page.emulate_media(reduced_motion='reduce')
            page.reload(wait_until='networkidle')
            page.evaluate('window.scrollBy(0,300)')
            page.wait_for_timeout(500)
            assert page.locator('.center-star-active').count()==0
            assert not errors,errors
            page.close()
        browser.close()
        print('320/390/768 touch: nearest-only, settle, once, no layout shift, links, reduced motion pass')
finally:
    server.shutdown()
