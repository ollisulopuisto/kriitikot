"""Distinguish expected cinema exclusions from broken parsers and missing HS stars."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from discovery_importer import DiscoveryImporter
from scrapers.hs import HSScraper
from scrapers.is_scraper import ISScraper


def html(asset):
    return '<script id="__NEXT_DATA__" type="application/json">'+json.dumps({'props': {'pageProps': {'page': {'assetData': asset}}}})+'</script>'


def test_is_expected_exclusions_are_not_parse_errors():
    scraper = ISScraper()
    assert scraper.exclusion_reason(html({'tags': [{'key': 'tv-lehti'}]})) == 'not_review'
    tv = {'tags': [{'key': 'tv-lehti'}, {'key': 'arviot'}], 'splitBody': [
        {'type': 'paragraph', 'crumbs': [{'content': 'Beetlejuice Beetlejuice TV5 klo 21.00.'}]},
        {'type': 'paragraph', 'crumbs': [{'content': 'Musta komedia ★★★★', 'marks': ['endnote']}]}]}
    assert scraper.exclusion_reason(html(tv)) == 'outside_cinema'
    assert scraper.exclusion_reason('<html>unexpected payload</html>') is None


def test_hs_public_review_headline_can_supply_explicit_rating_only():
    scraper = HSScraper()
    assert scraper._extract_rating({'storyLogo': 'Elokuva-arvio', 'title': 'Dokumentti täyttää odotukset: viisi tähteä'}) == 5
    assert scraper._extract_rating({'title': 'Näyttelijän viisi tähteä'}) is None
    assert scraper._extract_rating({'storyLogo': 'Elokuva-arvio', 'title': 'Viiden tähden hotellissa'}) is None


def test_hs_preview_recovery_requires_verified_article_and_existing_film():
    importer = DiscoveryImporter.__new__(DiscoveryImporter)
    importer.session = MagicMock()
    importer.session.query.return_value.filter_by.return_value.first.return_value = SimpleNamespace(title='You Can See Everything')
    url = 'https://www.hs.fi/popkulttuuri/art-2000012404132.html'
    asset = {'id':2000012404132, 'metaTitle':'Dokumentti You Can See Everything vakuuttaa',
             'ingress':'Dokumentissa You Can See Everything tekijät yhdistävät keinonsa.'}
    assert importer.resolve_hs_preview_title(asset, url) == 'You Can See Everything'
    assert importer.resolve_hs_preview_title(asset, 'https://www.hs.fi/another') is None
    assert importer.resolve_hs_preview_title({'metaTitle':'Top Gun: Maverick', 'ingress':'Top Gun: Maverick'}, url) is None
    assert importer.resolve_hs_preview_title({**asset,'ingress':'Unknown movie'}, url) is None
    importer.session.query.return_value.filter_by.return_value.first.return_value = None
    assert importer.resolve_hs_preview_title(asset, url) is None


def test_episodi_film_card_not_the_article_headline():
    from scrapers.episodi import EpisodiScraper
    scraper = EpisodiScraper()
    page = '<h1>Arvio: Lorcan teos innoitti viiden tähden elokuvan</h1><h2 class="epi-rv-n">La bola negra</h2>'
    assert scraper._extract_title(scraper.get_soup(page)) == 'La bola negra'
    structured = '<h1>Misleading headline</h1><script type="application/ld+json">'+json.dumps({'@type':'Review','itemReviewed':{'@type':'Movie','name':'Dry Leaf'}})+'</script>'
    assert scraper._extract_title(scraper.get_soup(structured)) == 'Dry Leaf'
    assert scraper.parse_html(structured + '<h2 class="epi-rv-n">Wrong film</h2>') is None
    assert scraper.parse_html('<h1>A headline without film identity</h1>') is None


def test_importer_separates_is_skips_from_true_parse_failures(monkeypatch):
    from models import Base, get_session, Publication
    from sqlalchemy import create_engine
    import discovery_importer
    importer = DiscoveryImporter.__new__(DiscoveryImporter)
    importer.source_failures = {}
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    importer.session = get_session(engine)
    importer.session.add(Publication(name='Ilta-Sanomat',short_name='is'))
    importer.session.commit()
    importer.scrapers={'is':ISScraper()}
    importer.meta_scraper=SimpleNamespace(discover_new_reviews=lambda *a:[{'url':'https://www.is.fi/example','title':'Not a cinema review'}])
    response = SimpleNamespace(text=html({'tags':[{'key':'tv-lehti'}]}),raise_for_status=lambda:None)
    monkeypatch.setattr(discovery_importer.requests,'get',lambda *a,**k:response)
    assert importer.import_discovered_reviews('is') == 0
    assert importer.source_failures == {'is':0}
    response.text='<html>Unexpected changed layout</html>'
    assert importer.import_discovered_reviews('is') == 0
    assert importer.source_failures == {'is':1}
    importer.session.close()


def test_episodi_api_title_is_not_article_headline(monkeypatch):
    from scrapers.episodi import EpisodiScraper
    import scrapers.episodi
    item = {'title': {'rendered': 'Misleading article headline'},
            'content': {'rendered': '<h2 class="epi-rv-n">Dry Leaf</h2>'},
            'link': 'https://www.episodi.fi/elokuvat/dry-leaf/'}
    response = SimpleNamespace(json=lambda:[item], raise_for_status=lambda:None)
    monkeypatch.setattr(scrapers.episodi.requests,'get',lambda *a,**k:response)
    assert EpisodiScraper().parse_json_api()[0].movie_title == 'Dry Leaf'


def test_is_discovers_kari_jarvinen_cinema_review():
    from discovery import CategoryCrawler
    from bs4 import BeautifulSoup
    item = {'byLine':'Kari Järvinen','title':'Vuoden erikoisin kotimainen elokuva',
            'url':'/tv-ja-elokuvat/art-2000012425541.html','ingress':'Kauhu piinaa katsojaa.'}
    payload={'props':{'pageProps':{'page':{'data':{'data':[{'lanes':[{'items':[item]}]}]}}}}}
    soup=BeautifulSoup('<script id="__NEXT_DATA__">'+json.dumps(payload)+'</script>','html.parser')
    found=CategoryCrawler()._find_is_reviews(soup,10)
    assert len(found) == 1
    assert found[0]['url'].endswith('art-2000012425541.html')


def test_is_punaista_lunta_cinema_endnote_not_tv_exclusion():
    page=html({'byLine':'Kari Järvinen','metaTitle':'Punaista lunta: Uusi kauhukomedia','tags':[{'key':'tv-lehti'},{'key':'arviot'}],
               'splitBody':[{'type':'paragraph','crumbs':[{'content':'Punaista lunta','marks':['em']}]},
                            {'type':'paragraph','crumbs':[{'content':'Punaista lunta, ensi-ilta elokuvateattereissa perjantaina 20.11.','marks':['endnote']}]},
                            {'type':'paragraph','crumbs':[{'content':'Kauhukomedia ★★★','marks':['endnote']}]}]})
    scraper=ISScraper()
    assert scraper.exclusion_reason(page) is None
    parsed=scraper.parse_html(page)
    assert (parsed.movie_title,parsed.critic_name,parsed.rating_stars)==('Punaista lunta','Kari Järvinen',3)


def test_hs_transformed_headline_is_still_missing_film_facts(monkeypatch):
    from models import Base, get_session, Publication, Movie
    from sqlalchemy import create_engine
    import discovery_importer
    importer=DiscoveryImporter.__new__(DiscoveryImporter)
    importer.source_failures={}
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    importer.session=get_session(engine)
    importer.session.add(Publication(name='Helsingin Sanomat',short_name='hs'))
    importer.session.commit()
    importer.scrapers={'hs':HSScraper()}
    importer.meta_scraper=SimpleNamespace(discover_new_reviews=lambda *a:[{'url':'https://www.hs.fi/example','title':'Preview'}])
    payload=html({'storyLogo':'Elokuva-arvio','title':'Elokuva-arvio | Dokumentti täyttää odotukset: viisi tähteä', 'splitBody':[]})
    response=SimpleNamespace(text=payload,raise_for_status=lambda:None)
    monkeypatch.setattr(discovery_importer.requests,'get',lambda *a,**k:response)
    assert importer.import_discovered_reviews('hs') == 0
    assert importer.source_failures == {'hs':1}
    assert importer.session.query(Movie).count() == 0
    importer.session.close()


def test_is_tagged_review_without_body_is_an_error_not_exclusion():
    assert ISScraper().exclusion_reason(html({'tags':[{'key':'tv-lehti'},{'key':'arviot'}],
        'title':'Uusi kotimainen kauhukomedia vakuuttaa'})) is None


def test_is_exclusions_share_the_cinema_policy_evidence():
    scraper=ISScraper()
    base={'tags':[{'key':'tv-lehti'},{'key':'arviot'}]}
    for metadata, endnote in [({},'Draama Ruutu ★★★'),({},'Draama Yle Teema ★★★'),
                               ({'title':'Netflix-draama'},'Draama ★★★'),
                               ({'ingress':'Suoratoistopalvelu esittää tämän.'},'Draama ★★★')]:
        asset={**base,**metadata,'splitBody':[{'type':'paragraph','crumbs':[{'content':endnote,'marks':['endnote']}]}]}
        assert scraper.parse_html(html(asset)) is None
        assert scraper.exclusion_reason(html(asset)) == 'outside_cinema'


def test_is_plot_clock_time_is_not_broadcast_evidence():
    asset={'tags':[{'key':'tv-lehti'},{'key':'arviot'}], 'ingress':'Elokuvan ensi-ilta on perjantaina.',
           'byLine':'Kari Järvinen','splitBody':[
               {'type':'paragraph','crumbs':[{'content':'Punaista lunta','marks':['em']}]},
               {'type':'paragraph','crumbs':[{'content':'Ryöstö alkaa klo 12.30 ja etenee reaaliajassa.'}]},
               {'type':'paragraph','crumbs':[{'content':'Draama ★★★','marks':['endnote']}]}]}
    scraper=ISScraper()
    assert scraper.exclusion_reason(html(asset)) is None
    assert scraper.parse_html(html(asset)).movie_title == 'Punaista lunta'


def test_is_broadcast_schedule_case_and_channel_variants():
    scraper = ISScraper()
    for clock in ('klo', 'Klo', 'KLO'):
        for channel in ('TV5', 'Yle', 'Nelonen', 'Sub'):
            for endnote in (True, False):
                asset = {'tags': [{'key': 'tv-lehti'}, {'key': 'arviot'}], 'splitBody': [
                    {'type': 'paragraph', 'crumbs': [{'content': f'{clock} 21.00 {channel}',
                                                     'marks': ['endnote'] if endnote else []}]},
                    {'type': 'paragraph', 'crumbs': [{'content': 'Komedia ★★★'}]}]}
                assert scraper.exclusion_reason(html(asset)) == 'outside_cinema', (clock, channel, endnote)
                assert scraper.parse_html(html(asset)) is None


def test_episodi_api_rejects_untrusted_article_origins_and_redirects(monkeypatch):
    from scrapers.episodi import EpisodiScraper
    import scrapers.episodi
    scraper = EpisodiScraper()
    bad_urls = ('http://www.episodi.fi/elokuvat/test/', 'https://episodi.fi.attacker.test/',
                'https://attacker.test/', 'https://127.0.0.1/', '//episodi.fi/test',
                'https://user@episodi.fi/test', 'https://episodi.fi:8443/test',
                'https://[bad', None)
    for url in bad_urls:
        calls = []
        def get(target, **kwargs):
            calls.append(target)
            return SimpleNamespace(json=lambda:[{'link':url,'content':{'rendered':''}}],
                                   raise_for_status=lambda:None)
        monkeypatch.setattr(scrapers.episodi.requests, 'get', get)
        assert scraper.parse_json_api() == []
        assert calls == [scraper.api_url]
    for host in ('episodi.fi', 'www.episodi.fi'):
        url = f'https://{host}/elokuvat/test/'
        for status in (200, 302):
            calls = []
            def get(target, **kwargs):
                calls.append((target, kwargs))
                if target == scraper.api_url:
                    return SimpleNamespace(json=lambda:[{'link':url,'content':{'rendered':''}}],
                                           raise_for_status=lambda:None)
                return SimpleNamespace(status_code=status, text='<h2 class="epi-rv-n">Dry Leaf</h2>',
                                       headers={'Location':'http://127.0.0.1/private'}, raise_for_status=lambda:None)
            monkeypatch.setattr(scrapers.episodi.requests, 'get', get)
            reviews = scraper.parse_json_api()
            assert len(reviews) == (1 if status == 200 else 0)
            assert len(calls) == 2
            assert calls[-1][1]['allow_redirects'] is False


def test_discovery_errors_are_not_empty_successes(monkeypatch):
    import requests
    from discovery import CategoryCrawler
    import discovery
    import pytest
    crawler = CategoryCrawler()
    def outage(*a, **k):
        raise requests.ConnectionError('offline')
    monkeypatch.setattr(discovery.requests, 'get', outage)
    for source in crawler.CATEGORY_PAGES:
        with pytest.raises(Exception):
            crawler.find_review_links(source)
    for source in ('episodi', 'kulttuuritoimitus', 'demokraatti'):
        # Demokraatti first fetches its category before its API.
        response = SimpleNamespace(text='<html></html>',raise_for_status=lambda:None,
                                   json=lambda: (_ for _ in ()).throw(ValueError('bad JSON')))
        monkeypatch.setattr(discovery.requests, 'get', lambda *a,**k:response)
        with pytest.raises(Exception):
            crawler.find_review_links(source)
    monkeypatch.setattr(discovery.requests, 'get',lambda *a,**k:SimpleNamespace(
        json=lambda:[],raise_for_status=lambda:None))
    assert crawler.find_review_links('episodi') == []


def test_importer_records_discovery_failure_but_not_valid_empty():
    importer = DiscoveryImporter.__new__(DiscoveryImporter)
    importer.source_failures = {}
    def fail(*a):
        raise ValueError('Discovery failed')
    importer.meta_scraper = SimpleNamespace(discover_new_reviews=fail)
    assert importer.import_discovered_reviews('episodi') == 0
    assert importer.source_failures == {'episodi':1}
    importer.meta_scraper.discover_new_reviews = lambda *a:[]
    assert importer.import_discovered_reviews('episodi') == 0
    assert importer.source_failures == {'episodi':0}


def test_hs_headline_conversion_uses_shared_parser(monkeypatch):
    scraper = HSScraper()
    calls = []
    monkeypatch.setattr(scraper,'parse_rating', lambda text: calls.append(text) or 4)
    assert scraper._extract_rating({'storyLogo':'Elokuva-arvio','title':'Dokumentti: neljä tähteä'}) == 4
    assert calls == ['neljä tähteä']


def test_next_discovery_missing_or_malformed_payload_is_error():
    import pytest
    from bs4 import BeautifulSoup
    from discovery import CategoryCrawler
    crawler = CategoryCrawler()
    for method in (crawler._find_hs_reviews,crawler._find_is_reviews):
        for body in ('<html>Error page</html>', '<script id="__NEXT_DATA__">{</script>',
                     '<script id="__NEXT_DATA__">{}</script>'):
            with pytest.raises(Exception):
                method(BeautifulSoup(body,'html.parser'),10)
        payload = {'props':{'pageProps':{'page':{'data':{'data':[]}}}}}
        assert method(BeautifulSoup('<script id="__NEXT_DATA__">'+json.dumps(payload)+'</script>','html.parser'),10) == []


def test_all_source_discovery_failures_are_counted(monkeypatch):
    from discovery import CategoryCrawler, MetaScraper
    import discovery
    def outage(*a,**k):
        raise OSError('offline')
    monkeypatch.setattr(discovery.requests,'get',outage)
    importer = DiscoveryImporter.__new__(DiscoveryImporter)
    importer.source_failures = {}
    importer.meta_scraper = MetaScraper()
    importer.session = MagicMock()
    assert all(value == 0 for value in importer.import_all_sources().values())
    assert importer.source_failures == {source:1 for source in CategoryCrawler.CATEGORY_PAGES}
