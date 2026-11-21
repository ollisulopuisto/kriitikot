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
            # grow proportionally; five can overflow the face, never its tap target.
            page.evaluate('''() => {
                const fixture=document.createElement('div');fixture.id='rating-fixture';
                fixture.style='display:flex;flex-wrap:wrap;gap:12px;background:white;padding:20px';
                for(let n=1;n<=5;n++)for(const url of ['https://example.com/',''])
                    fixture.insertAdjacentHTML('beforeend', '<div class="review-item">'+createReviewPill({rating_stars:n,source_url:url,source_publication:'hs'})+'</div>');
                document.body.prepend(fixture);
            }''')
            assert page.locator('#rating-fixture .rating-pill').count() == 10
            measure = '''pills=>pills.map(p=>{
                const s=p.querySelector('.rating-stars'),r=s.getBoundingClientRect(),target=p.getBoundingClientRect();
                return {w:r.width,h:r.height,target:target.height,text:s.textContent.length,
                    slots:s.children.length,empty:s.querySelectorAll('.rating-star-empty').length,
                    ink:getComputedStyle(s).color,bg:getComputedStyle(s).backgroundImage,
                    fs:parseFloat(getComputedStyle(s).fontSize),
                    proportional:[...s.children].every(c=>getComputedStyle(c).transform==='none'),
                    glow:getComputedStyle(s.firstElementChild).textShadow,
                    faceShadow:getComputedStyle(s).boxShadow,
                    crownUnclipped:[...s.children].every(c=>{
                        let node=c;
                        while(node && node!==document.body){
                            const style=getComputedStyle(node);
                            if(['hidden','clip','scroll','auto'].includes(style.overflowX) ||
                               ['hidden','clip','scroll','auto'].includes(style.overflowY)) return false;
                            node=node.parentElement;
                        }
                        return true;
                    }),
                    // Measure painted glyph ink, not flex slots. Empty slots use
                    // the same glyph via ::before. Overlap between adjacent stars
                    // is intended; escaping the link target is not.
                    inTarget:[...s.children].every(c=>{
                        const b=c.getBoundingClientRect(),style=getComputedStyle(c);
                        const ctx=document.createElement('canvas').getContext('2d');
                        ctx.font=`${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
                        const m=ctx.measureText('★');
                        const x=b.left+(b.width-m.width)/2;
                        const baseline=b.top+(b.height-(m.fontBoundingBoxAscent+m.fontBoundingBoxDescent))/2+m.fontBoundingBoxAscent;
                        return x-m.actualBoundingBoxLeft>=target.left-.5 &&
                            x+m.actualBoundingBoxRight<=target.right+.5 &&
                            baseline-m.actualBoundingBoxAscent>=target.top-.5 &&
                            baseline+m.actualBoundingBoxDescent<=target.bottom+.5;
                    })};
            })'''
            geometry = page.locator('#rating-fixture .rating-pill').evaluate_all(measure)
            assert all(p['slots'] == 5 and p['empty'] == 5-p['text'] for p in geometry)
            assert all(p['proportional'] and p['inTarget'] and p['crownUnclipped'] and p['ink'] == 'rgb(255, 255, 255)' for p in geometry), geometry
            assert [p['fs'] for p in geometry[::2]] == [12, 14, 17, 22, 29], geometry
            assert all('34, 197, 94' in p['glow'] for p in geometry[-2:]), geometry
            assert all('34, 197, 94' not in p['faceShadow'] for p in geometry), geometry
            if width < 769:
                assert all(p['target'] >= 44 for p in geometry), geometry
                actual_targets = page.locator('.movie-card a.rating-pill').evaluate_all(
                    'nodes=>nodes.filter(n=>n.getBoundingClientRect().height>0).map(n=>n.getBoundingClientRect().height)')
                assert actual_targets and min(actual_targets) >= 44, actual_targets
            assert all(abs(p['w'] - 88) < .1 and abs(p['h'] - 17) < .1 for p in geometry), geometry
            # Negative controls: horizontal-only escape and the old face height must
            # fail the same measurements, rather than only passing good CSS.
            broken = page.add_style_tag(content='#rating-fixture .stars-5 .rating-star { position:relative; left:100px!important }')
            assert not all(p['inTarget'] for p in page.locator('#rating-fixture .rating-pill').evaluate_all(measure))
            broken.evaluate('n=>n.remove()')
            old_face = page.add_style_tag(content='#rating-fixture .rating-stars { height:28.8px!important }')
            assert not all(abs(p['h'] - 17) < .1 for p in page.locator('#rating-fixture .rating-pill').evaluate_all(measure))
            old_face.evaluate('n=>n.remove()')
            clipping = page.add_style_tag(content='#rating-fixture .rating-stars { overflow:hidden!important }')
            assert not all(p['crownUnclipped'] for p in page.locator('#rating-fixture .rating-pill').evaluate_all(measure))
            clipping.evaluate('n=>n.remove()')
            page.screenshot(path=str(output / f'scale-{width}.png'))
            page.locator('#rating-fixture').evaluate('e=>e.remove()')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
            page.screenshot(path=str(output / f'context-{width}.png'))
            if width >= 769:
                page.locator('#windowing-toggle').check()
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
