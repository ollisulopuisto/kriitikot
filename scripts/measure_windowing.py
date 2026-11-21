"""Local Chromium measurement, never contacts the scraper or production."""
import json, subprocess, time, os, argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--label',default='baseline');p.add_argument('--root',default=str(Path(__file__).resolve().parents[1]));a=p.parse_args()
root=Path(a.root);out=Path(os.environ.get('SCREENSHOT_DIR','/tmp/kriitikot-windowing'));out.mkdir(exist_ok=True)
server=subprocess.Popen([str(root/'.venv/bin/python'),'-m','flask','--app','src/app','run','--port','5433'],cwd=root,env={**os.environ,'PYTHONPATH':str(root/'src')},stdout=open('/tmp/kriitikot-window-server.log','w'),stderr=subprocess.STDOUT)
try:
 time.sleep(1)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/google-chrome-stable',headless=True,args=['--no-sandbox'])
  results={}
  for name,width,height in [('desktop',1600,900),('phone',390,844)]:
   page=browser.new_page(viewport={'width':width,'height':height});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   cdp=page.context.new_cdp_session(page);cdp.send('Performance.enable')
   page.goto('http://127.0.0.1:5433');page.wait_for_function('window._cachedReviewsData && window.currentMovieOffset >= 30');page.evaluate('document.fonts.ready');page.wait_for_timeout(300)
   def metrics():
    m=page.evaluate('''() => ({elements:document.querySelectorAll('*').length,rows:document.querySelectorAll('tbody tr:not(.window-spacer)').length,cards:document.querySelectorAll('.movie-card').length,cells:document.querySelectorAll('tbody td').length,loaded:window.currentMovieOffset,scrollHeight:document.documentElement.scrollHeight})''')
    perf={v['name']:v['value'] for v in cdp.send('Performance.getMetrics')['metrics']};m.update({k:perf.get(k) for k in ['JSHeapUsedSize','LayoutDuration','RecalcStyleDuration','TaskDuration']});return m
   initial=metrics();page.screenshot(path=str(out/f'{a.label}-{name}.png'))
   start=time.perf_counter()
   page.evaluate('''() => { while(window.currentMovieOffset < Object.keys(window._cachedReviewsData).length) window.loadMoreMovies(30); }''');page.wait_for_timeout(300)
   loaded_ms=(time.perf_counter()-start)*1000;all_loaded=metrics()
   frames=page.evaluate('''async () => {const frames=[];let last=performance.now();for(let i=0;i<60;i++){window.scrollBy(0,140);await new Promise(requestAnimationFrame);const now=performance.now();frames.push(now-last);last=now;}return frames;}''')
   page.wait_for_timeout(200);scrolled=metrics();page.screenshot(path=str(out/f'{a.label}-{name}-scrolled.png'))
   results[name]={'initial':initial,'allLoaded':all_loaded,'scrolled':scrolled,'loadAllMs':round(loaded_ms,1),'frameIntervalsMs':frames,'errors':errors}
   page.close()
  browser.close()
 (out/f'{a.label}.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
finally:
 server.terminate();server.wait()
