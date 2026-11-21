"""Chromium A1v3c smoke, no scrape or deployment.

Install project requirements and Playwright, BeautifulSoup4 and Jinja2.
System Chrome is required (or set CHROME_BIN).
"""
import functools
import http.server
import os
from pathlib import Path
import threading

try:
    from bs4 import BeautifulSoup
    from jinja2 import Environment, FileSystemLoader
    from playwright.sync_api import sync_playwright
except ImportError as error:
    raise SystemExit(
        'Install project requirements, playwright, beautifulsoup4 and jinja2. '
        f'Missing module: {error.name}'
    ) from error

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('SCREENSHOT_DIR', '/tmp/kriitikot-cluster-check'))
OUT.mkdir(parents=True, exist_ok=True)
ENV = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=True)
ENV.filters['publication_name'] = str
POSITIONS = {
    1: [(50, 32)], 2: [(38, 32), (62, 32)],
    3: [(50, 18), (38, 44), (62, 44)],
    4: [(35, 18), (65, 18), (35, 46), (65, 46)],
    5: [(37, 20), (63, 20), (24, 43), (50, 43), (76, 43)],
}
MEASURE = '''p=>{
    const face=p.querySelector('.rating-stars'),f=face.getBoundingClientRect();
    const cell=p.closest('td');
    const cellBounds=cell?.getBoundingClientRect();
    const fitsCell=!cellBounds || (f.left>=cellBounds.left &&
        f.right<=cellBounds.right);
    const stars=[...face.children].filter(n=>getComputedStyle(n).display!=='none');
    return {width:f.width,height:f.height,fitsCell,text:face.textContent,
        label:face.getAttribute('aria-label'),
        shape:getComputedStyle(stars[0],'::before').clipPath,
        glow:getComputedStyle(stars[0]).filter,
        faceShadow:getComputedStyle(face).boxShadow,
        ink:getComputedStyle(stars[0],'::after').backgroundColor,
        edge:getComputedStyle(stars[0],'::before').backgroundColor,
        stars:stars.map(n=>{
            const b=n.getBoundingClientRect();
            let clear=b.left>=f.left && b.right<=f.right &&
                b.top>=f.top && b.bottom<=f.bottom;
            for(let a=n;a && a!==document.body;a=a.parentElement){
                const cs=getComputedStyle(a),r=a.getBoundingClientRect();
                const x=r.left+a.clientLeft,y=r.top+a.clientTop;
                if(['hidden','clip','auto','scroll'].includes(cs.overflowX))
                    clear &&= b.left>=x-.5 && b.right<=x+a.clientWidth+.5;
                if(['hidden','clip','auto','scroll'].includes(cs.overflowY))
                    clear &&= b.top>=y-.5 && b.bottom<=y+a.clientHeight+.5;
            }
            return {x:b.x+b.width/2-f.x,y:b.y+b.height/2-f.y,
                w:b.width,h:b.height,clear};
        })};
}'''


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def server_pill(rating, linked, phone):
    review = dict(rating_stars=rating,
                  source_url='https://example.com/' if linked else '',
                  review_text='', publication=dict(short_name='hs', name='HS'))
    html = ENV.get_template(
        '_movie_card.html' if phone else '_movie_row.html'
    ).render(movie_title='Test', critics_reviews={'Test': [review]},
             all_critics=[dict(name='Test', id='test')], poster_urls={},
             nytleffaan_urls={}, letterboxd_urls={}, movie_review_counts={},
             movie_rating_distributions={})
    return str(BeautifulSoup(html, 'html.parser').select_one('.rating-pill'))


def verify(pill, rating):
    data = pill.evaluate(MEASURE)
    assert data['width'] == 100 and data['height'] == 64, data
    assert data['text'] == '★' * rating, data
    assert data['label'] == f'{rating}/5 tähteä', data
    assert data['shape'].startswith('polygon('), data
    assert data['fitsCell'], data
    assert data['faceShadow'] == 'none', data
    assert data['ink'] == ['rgb(185, 28, 28)', 'rgb(168, 58, 18)',
                           'rgb(212, 167, 0)', 'rgb(22, 134, 187)',
                           'rgb(23, 148, 71)'][rating - 1], data
    if rating == 3:
        assert data['edge'] == 'rgb(140, 113, 0)', data
    assert len(data['stars']) == rating, data
    assert all(s['clear'] for s in data['stars']), data
    size = [18, 20, 22, 24, 25][rating - 1]
    for star, (x, y) in zip(data['stars'], POSITIONS[rating]):
        assert abs(star['x'] - x) < .1 and abs(star['y'] - y) < .1
        assert star['w'] == size and star['h'] == size
    assert ('drop-shadow' in data['glow']) == (rating == 5)


server = http.server.ThreadingHTTPServer(
    ('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT / 'docs'))
)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=os.environ.get(
                'CHROME_BIN', '/usr/bin/google-chrome-stable'),
            args=['--no-sandbox'])
        for width in (320, 390, 900, 1600):
            page = browser.new_page(viewport={'width': width, 'height': 900})
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}',
                      wait_until='networkidle')
            page.wait_for_function('window.currentMovieOffset>=60')
            if width >= 769:
                page.locator('#windowing-toggle').check()
            page.evaluate('window.reviewWindow.prepare()')
            selector = ('.movie-card .rating-pill' if width < 769 else
                        '#review-container-desktop td .rating-pill')
            # One known real ancestor; replace, never crowd a narrow lane.
            slot = page.locator(selector).first
            host = slot.evaluate_handle('p=>p.parentElement')
            original = slot.evaluate('p=>p.outerHTML')
            page.evaluate('''() => {
                const scale=document.createElement('div');scale.id='scale';
                scale.style='display:flex;gap:12px;flex-wrap:wrap;padding:20px';
                for(let n=1;n<=5;n++)scale.insertAdjacentHTML('beforeend',
                    createReviewPill({rating_stars:n,source_url:'',
                        source_publication:'hs'}));
                document.body.prepend(scale);
            }''')
            page.screenshot(path=str(OUT / f'scale-{width}.png'))
            page.locator('#scale').evaluate('n=>n.remove()')
            for origin in ('server', 'lazy'):
                for linked in (False, True):
                    for rating in range(1, 6):
                        html = server_pill(rating, linked, width < 769)
                        if origin == 'lazy':
                            html = page.evaluate('''r=>createReviewPill(r)''', {
                                'rating_stars': rating,
                                'source_url': 'https://example.com/'
                                if linked else '', 'source_publication': 'hs'})
                        pill = host.evaluate_handle('''(host,html)=>{
                            host.querySelector('.rating-pill').outerHTML=html;
                            return host.querySelector('.rating-pill');
                        }''', html).as_element()
                        pill.scroll_into_view_if_needed()
                        assert pill.evaluate('p=>p.tagName') == (
                            'A' if linked else 'SPAN')
                        verify(pill, rating)
                        if linked:
                            before = pill.evaluate(MEASURE)
                            pill.hover()
                            page.wait_for_timeout(180)
                            assert pill.evaluate(MEASURE) == before
                            pill.focus()
                            assert pill.evaluate(
                                "p=>getComputedStyle(p).outlineStyle") != 'none'
                        # Negative: horizontal escape and ancestor clipping.
                        bad = page.add_style_tag(content=(
                            '.rating-star {left:110px!important}'))
                        assert not all(s['clear'] for s in
                                       pill.evaluate(MEASURE)['stars'])
                        bad.evaluate('n=>n.remove()')
                        clip_host = pill.evaluate_handle('''p=>
                            p.closest('.review-item') ||
                            p.closest('.table-wrapper')''')
                        saved = clip_host.evaluate('''h=>{
                            const old=h.getAttribute('style');
                            Object.assign(h.style,{height:'1px',
                                maxHeight:'1px',minHeight:'0',overflow:'hidden'});
                            return old;
                        }''')
                        assert not all(s['clear'] for s in
                                       pill.evaluate(MEASURE)['stars'])
                        clip_host.evaluate('''(h,old)=>old===null
                            ?h.removeAttribute('style'):h.setAttribute(
                                'style',old)''', saved)
                        verify(pill, rating)
            host.evaluate('''(h,html)=>{
                h.querySelector('.rating-pill').outerHTML=html;
            }''', original)
            page.evaluate('window.scrollTo(0,0)')
            page.screenshot(path=str(OUT / f'context-{width}.png'))
            assert page.evaluate(
                'document.documentElement.scrollWidth<=innerWidth')
            page.emulate_media(reduced_motion='reduce')
            assert page.locator(selector).first.evaluate(
                "p=>getComputedStyle(p).animationName") == 'none'
            assert not errors, errors
            print(width, 'server/lazy linked/unlinked 1-5 geometry passed')
            page.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
