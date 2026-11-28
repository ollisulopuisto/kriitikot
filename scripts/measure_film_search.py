from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from threading import Thread
from playwright.sync_api import sync_playwright
import json,sys
root=Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*_):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(root/'docs')));Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/google-chrome-stable',args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1600,'height':900});page.goto(f'http://127.0.0.1:{server.server_port}',wait_until='networkidle');page.wait_for_function('window.currentMovieOffset>=60')
 page.evaluate('''() => {window.perfCalls={}; for(const name of ['topUpSliderResults','reconcileFacetVisibility','reapplyAllFacets','refreshStickyHeader','loadMoreMovies','renderMovie','syncFillerCells','updateCriticColumnVisibility','matchesFilmSearch']){const orig=window[name];if(typeof orig!=='function')continue;window[name]=function(...args){if(['updateCriticColumnVisibility','reconcileFacetVisibility'].includes(name)&&window.facetReapplyDepth)return orig.apply(this,args);const t=performance.now();try{return orig.apply(this,args)}finally{const s=perfCalls[name]??={count:0,ms:0};s.count++;s.ms+=performance.now()-t;}}}window.longTasks=[];new PerformanceObserver(l=>longTasks.push(...l.getEntries().map(e=>e.duration))).observe({type:'longtask'});}''')
 for value in ['k','ki','kis','kiss','']:
  page.evaluate('window.perfCalls={};window.longTasks=[]');page.locator('.film-search').first.fill(value);page.wait_for_timeout(550);print(value,page.evaluate('({calls:perfCalls,longTasks,cards:document.querySelectorAll(".movie-card").length,rows:document.querySelectorAll("tbody tr").length})'))
 page.screenshot(path='/tmp/kriitikot-search-measure.png');b.close()
server.shutdown()
