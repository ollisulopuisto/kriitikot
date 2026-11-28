"""Reproduce stale unversioned cache entries without a user profile or deployment."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from subprocess import check_output
from threading import Thread
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(root/'docs')))
Thread(target=server.serve_forever, daemon=True).start()
# The deployed predecessor used unversioned URLs, 32px search margins and no summary.
old = {path: check_output(['git', 'show', f'05d22e8d66b000b71922dfd0828607a9a06e8737:docs/{path}'], cwd=root)
       for path in ('static/css/filters.css', 'static/app.js', 'static/ui.js')}
try:
    with sync_playwright() as p:
        for engine in ('chromium', 'webkit'):
            try:
                browser = getattr(p, engine).launch(**({'executable_path': '/usr/bin/google-chrome', 'args': ['--no-sandbox']} if engine == 'chromium' else {}))
            except Exception as error:
                if engine != 'webkit':
                    raise
                print('WebKit unavailable:', str(error).splitlines()[0])
                continue
            page = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
            # Exact old URL cache entries must not satisfy the newly hashed requests.
            def cached_response(body, path):
                def respond(route):
                    route.fulfill(body=body, content_type='text/css' if path.endswith('.css') else 'text/javascript')
                return respond
            for path, body in old.items():
                page.route(f'**/{path}', cached_response(body, path))
            page.goto(f'http://127.0.0.1:{server.server_port}', wait_until='networkidle')
            page.locator('#mobile-filter-toggle').click()
            page.wait_for_timeout(350)
            search = page.locator('.mobile-film-search input')
            group = page.locator('.mobile-filter-group').first
            assert abs(search.bounding_box()['x'] - group.bounding_box()['x']) < 1
            assert abs(search.bounding_box()['width'] - group.bounding_box()['width']) < 1
            page.screenshot(path=f'/downloads/inset-fixed-{engine}.png')
            search.fill('You Can See Everything')
            page.wait_for_timeout(250)
            page.locator('#mobile-filter-toggle').click()
            page.wait_for_timeout(350)
            assert page.locator('.toggle-text').text_content() == 'Haku: you can see everything'
            assert page.locator('.mobile-filter-clear').is_visible()
            assert page.locator('.mobile-filter').evaluate('n=>n.classList.contains("has-active-filters")')
            page.screenshot(path=f'/downloads/summary-fixed-{engine}.png')
            browser.close()
            print(engine, 'stale-cache bypass, aligned input, active-query summary and clear pass')
finally:
    server.shutdown()
    server.server_close()
