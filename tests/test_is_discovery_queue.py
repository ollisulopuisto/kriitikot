"""IS discovery uses article evidence, a persistent backlog and bounded requests."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from datetime import datetime, timedelta
from types import SimpleNamespace
import pytest
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from models import Base, get_session, Movie, Publication, Review
from discovery import CategoryCrawler
from discovery_importer import DiscoveryImporter
from is_discovery_queue import ISDiscoveryQueue
from scrapers.is_scraper import ISScraper


def url(n):
    return f'https://www.is.fi/tv-ja-elokuvat/art-{n}.html'


def session():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return get_session(engine)


def page(asset):
    return '<script id="__NEXT_DATA__">'+json.dumps({'props':{'pageProps':{'page':{'assetData':asset}}}})+'</script>'


def review_asset(title='New Film'):
    return {'tags':[{'key':'tv-lehti'},{'key':'arviot'}], 'byLine':'Previously Unknown Critic',
        'title':'No review keyword or film name', 'splitBody':[{'type':'paragraph','crumbs':[
            {'type':'text','marks':['endnote'],'content':title+', ensi-ilta elokuvateattereissa. Draama ★★★'}]}]}


def test_discovery_ignores_authors_headlines_and_limit_deduplicates_cards():
    cards = [{'title':'Nothing recognizable','byLine':'Unknown Critic','url':url(123)},
             {'title':'Pinned duplicate','url':url(123)+'?tracking=x'},
             {'title':'Another','url':'/tv-ja-elokuvat/art-124.html'},
             {'url':'https://attacker.test/tv-ja-elokuvat/art-125.html'},
             {'url':'https://www.is.fi@attacker.test/tv-ja-elokuvat/art-126.html'}]
    data={'props':{'pageProps':{'page':{'data':{'data':[{'lanes':[{'items':cards}]}]}}}}}
    found=CategoryCrawler()._find_is_reviews(BeautifulSoup('<script id="__NEXT_DATA__">'+json.dumps(data)+'</script>','html.parser'),1)
    assert [item['url'] for item in found] == [url(123),url(124)]


def test_persistent_budget_backlog_retries_and_overlap(tmp_path):
    db=session();path=tmp_path/'queue.json';now=datetime(2026,11,20,10)
    candidates=[{'title':str(n),'url':url(n)} for n in range(5)]
    queue=ISDiscoveryQueue(db,path,now);queue.enqueue(candidates)
    assert [item['url'] for item in queue.due(2)] == [url(0),url(1)]
    queue.finish(url(0),'excluded');queue.finish(url(1),'failed')
    # A fresh process retains unfinished candidates even off the category page.
    queue=ISDiscoveryQueue(db,path,now+timedelta(hours=1));queue.enqueue([candidates[-1]])
    assert [item['url'] for item in queue.due(2)] == [url(2),url(3)]
    for n in (2,3,4):queue.finish(url(n),'excluded')
    assert queue.due(40) == []
    queue.now=now+timedelta(hours=13)
    assert [item['url'] for item in queue.due(40)] == [url(1)]
    queue.finish(url(1),'excluded')
    queue.now=now+timedelta(days=8)
    assert len(queue.due(40)) == 5
    assert queue.due(0) == []


def test_cached_success_is_retried_if_failed_workflow_did_not_save_review(tmp_path):
    db=session();path=tmp_path/'queue.json'
    queue=ISDiscoveryQueue(db,path);queue.enqueue([{'url':url(1),'title':'Film'}]);queue.finish(url(1),'imported')
    queue=ISDiscoveryQueue(db,path);queue.enqueue([])
    assert queue.due(40) == [{'url':url(1),'title':'Film'}]


def test_import_limit_after_classification_cache_and_real_errors(monkeypatch,tmp_path):
    import discovery_importer
    db=session();db.add(Publication(name='Ilta-Sanomat',short_name='is'))
    db.add_all([Movie(title='New Film'),Movie(title='Second Film')]);db.commit()
    importer=DiscoveryImporter.__new__(DiscoveryImporter);importer.session=db;importer.source_failures={}
    importer.is_cache_path=tmp_path/'queue.json';importer.scrapers={'is':ISScraper()}
    candidates=[{'title':'Uninformative headline','url':url(n)} for n in range(4)]
    importer.meta_scraper=SimpleNamespace(discover_new_reviews=lambda *a:candidates)
    assets=[{'tags':[{'key':'news'}]},review_asset(),review_asset('Second Film'),None]
    calls=[]
    def get(target,**kwargs):
        calls.append(target);assert kwargs['allow_redirects'] is False
        n=int(target.split('art-')[1].split('.')[0])
        return SimpleNamespace(text=page(assets[n]) if assets[n] else 'Broken layout',
                               status_code=200,raise_for_status=lambda:None)
    monkeypatch.setattr(discovery_importer.requests,'get',get)
    assert importer.import_discovered_reviews('is',limit=1,request_budget=2)==1
    assert calls==[url(0),url(1)]
    assert importer.is_stats=={'discovered':4,'requested':2,'admitted':1,'excluded':1,'failed':0,'queued':2}
    calls.clear()
    assert importer.import_discovered_reviews('is',limit=10,request_budget=1)==1
    assert calls==[url(2)]
    assert importer.is_stats['queued']==1
    calls.clear()
    assert importer.import_discovered_reviews('is',limit=10,request_budget=40)==0
    assert calls==[url(3)] and importer.source_failures['is']==1
    calls.clear()
    assert importer.import_discovered_reviews('is')==0
    assert calls==[] and importer.source_failures['is']==1
    assert db.query(Review).count()==2
    assert db.query(Review).first().critic.name=='Previously Unknown Critic'


def test_is_missing_tags_author_title_or_stars_needs_review():
    scraper=ISScraper()
    missing_tags=review_asset();missing_tags.pop('tags')
    assert scraper.exclusion_reason(page(missing_tags)) is None
    assert scraper.parse_html(page(missing_tags)) is None
    missing_author=review_asset();missing_author.pop('byLine')
    assert scraper.parse_html(page(missing_author)) is None
    no_title=review_asset();no_title['splitBody'][0]['crumbs'][0]['content']='Ensi-ilta elokuvateattereissa. Draama ★★★'
    assert scraper.parse_html(page(no_title)) is None
    no_stars=review_asset();no_stars['splitBody'][0]['crumbs'][0]['content']='New Film, ensi-ilta elokuvateattereissa.'
    assert scraper.parse_html(page(no_stars)) is None


def test_queue_rejects_cached_foreign_or_malformed_urls(tmp_path):
    db=session();path=tmp_path/'queue.json'
    queue=ISDiscoveryQueue(db,path)
    with pytest.raises(ValueError):
        queue.enqueue([{'url':'http://127.0.0.1/private','title':'bad'}])
    path.write_text(json.dumps({'version':1,'articles':{'http://127.0.0.1/private':{}}}))
    with pytest.raises(ValueError):
        ISDiscoveryQueue(db,path)


def test_edit_recheck_and_retry_fairness(tmp_path):
    db=session();path=tmp_path/'queue.json';now=datetime(2026,11,20,10)
    q=ISDiscoveryQueue(db,path,now)
    q.enqueue([{'url':url(n),'title':str(n)} for n in range(3)])
    for n in range(3):q.finish(url(n),'failed')
    q.now=now+timedelta(days=1)
    q.finish(url(0),'failed')
    # Repeated failures cannot permanently occupy the first retry slots.
    assert [i['url'] for i in q.due(1)] == [url(1)]
    q.finish(url(1),'excluded');q.finish(url(2),'excluded')
    q.now=now+timedelta(days=9)
    q.enqueue([{'url':url(1),'title':'Edited card'}])
    assert next(i for i in q.due(40) if i['url']==url(1))['title']=='Edited card'


def test_retry_clears_failure_after_unsaved_admissions(monkeypatch,tmp_path):
    import discovery_importer
    import time
    monkeypatch.setattr(time,'sleep',lambda *a:None)
    cache=tmp_path/'queue.json'
    candidates=[{'title':str(n),'url':url(n)} for n in range(11)]
    def importer():
        db=session();db.add(Publication(name='Ilta-Sanomat',short_name='is'))
        db.add_all([Movie(title=f'Film {n}') for n in range(11)]);db.commit()
        obj=DiscoveryImporter.__new__(DiscoveryImporter)
        obj.session=db;obj.source_failures={};obj.is_cache_path=cache;obj.scrapers={'is':ISScraper()}
        obj.meta_scraper=SimpleNamespace(discover_new_reviews=lambda *a:candidates)
        return obj
    broken=True;calls=[]
    def get(target,**kwargs):
        calls.append(target);n=int(target.split('art-')[1].split('.')[0])
        return SimpleNamespace(text='Broken' if n==0 and broken else page(review_asset(f'Film {n}')),
            status_code=200,raise_for_status=lambda:None)
    monkeypatch.setattr(discovery_importer.requests,'get',get)
    first=importer()
    assert first.import_discovered_reviews('is',limit=10)==10
    assert first.source_failures['is']==1
    # Simulate failed workflow: queue persisted, original DB is checked out.
    data=json.loads(cache.read_text())
    for row in data['articles'].values():row['checked_at']='2026-01-01T00:00:00'
    cache.write_text(json.dumps(data))
    broken=False;calls.clear();second=importer()
    assert second.import_discovered_reviews('is',limit=10)==10
    assert second.source_failures['is']==0
    assert calls[0]==url(0) and len(calls)<=40
