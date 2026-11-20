"""Real Chrome geometry/interaction check for the inline desktop toolbar.

Run with a Python environment that has Playwright installed. Uses system Chrome.
"""
import os
from pathlib import Path
import socket
import subprocess
import time
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.github' / 'screenshots' / 'inline-header'
OUT.mkdir(parents=True, exist_ok=True)
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
server = subprocess.Popen(
    [str(ROOT / '.venv/bin/python'), '-m', 'flask', '--app', 'src/app', 'run', '--port', str(port)],
    cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')},
    stdout=open('/tmp/inline-header-server.log', 'w'), stderr=subprocess.STDOUT,
)
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/google-chrome-stable', headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1600, 'height': 900})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        for _ in range(80):
            try:
                page.goto(f'http://127.0.0.1:{port}')
                break
            except Exception:
                time.sleep(.1)
        page.evaluate('document.fonts.ready')
        box = page.locator('.desktop-filters').bounding_box()
        assert abs(box['height'] - 128) < 1, box
        page.screenshot(path=str(OUT / 'desktop-1600.png'))
        for width in (1600, 1250, 1101, 1100, 769):
            page.set_viewport_size({'width': width, 'height': 900})
            for maxed in (False, True):
                for slider_id in ('min-reviews-slider', 'star-filter-slider'):
                    page.locator('#' + slider_id).evaluate('(e,maxed)=>{e.value=maxed?5:1;e.dispatchEvent(new Event("input",{bubbles:true}));}', maxed)
                for selector in ('.sorting-group', '.group-reviews', '.group-stars', '.group-favorites', '.media-group'):
                    r = page.locator('.desktop-filters ' + selector).bounding_box()
                    assert r['x'] >= 0 and r['x'] + r['width'] <= width, (width, selector, r)
                if width > 1100:
                    for group in ('.group-reviews', '.group-stars'):
                        label = page.locator(group + ' label').bounding_box()
                        track = page.locator(group + ' .slider-container').bounding_box()
                        assert label['x'] + label['width'] < track['x'], (width, group)
            page.locator('.desktop-filters [data-publication="HS"]').click()
            assert 'active' in page.locator('.desktop-filters [data-publication="HS"]').get_attribute('class')
            page.locator('#reset-filters-desktop').click()
        for width in (390, 320):
            page.set_viewport_size({'width': width, 'height': 844})
            page.reload()
            page.locator('#mobile-filter-toggle').click()
            page.locator('.mobile-filter [data-publication="HS"]').scroll_into_view_if_needed()
            page.locator('#reviews-plus-mobile').click()
            assert page.locator('#min-reviews-value-mobile').inner_text() == '2'
            page.locator('#stars-plus-mobile').click()
            assert page.locator('#star-filter-slider').input_value() == '2'
            for chip in page.locator('.mobile-filter .media-filter-btn').all():
                r = chip.bounding_box()
                assert r['height'] >= 44 and r['x'] >= 0 and r['x'] + r['width'] <= width, (width, r)
            page.screenshot(path=str(OUT / f'mobile-{width}.png'), animations='disabled')
        assert not errors, errors
        browser.close()
finally:
    server.terminate()
    server.wait()
