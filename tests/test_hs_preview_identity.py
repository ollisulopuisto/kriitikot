"""HS full-facts and current preview admission use source rating + known identity."""
import json
from pathlib import Path
from types import SimpleNamespace
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import pytest
from sqlalchemy import create_engine
from models import Base, get_session, Publication, Movie, Review
from discovery_importer import DiscoveryImporter
from scrapers.hs import HSScraper


def preview():
    return json.loads((Path(__file__).parent/'test_data/hs_dry_leaf_preview.json').read_text())


def document(asset):
    return '<script id="__NEXT_DATA__">'+json.dumps({'props':{'pageProps':{'page':{'assetData':asset}}}})+'</script>'


@pytest.mark.parametrize('title,rating',[
    ('Kriitikko antoi neljä tähteä elokuvalle',4),
    ('Viiden tähden sotaelokuva',5),('Elokuva: kaksi tähteä',2),
    ('Elokuva saa 3 tähteä',3),('Yhden tähden elokuva',1),
    ('Kolmen tähden draama',3),('Kahden tähden draama',2),
    ('Neljän tähden draama',4),('Ei arviota',None),
    ('Neljä tähteä vai viisi tähteä?',None),('Viiden tähden hotellissa tapahtuu murha',None),('Viiden tähden ravintolassa',None),('6 tähteä',None),('3.5 tähteä',None),('13 tähteä',None),
])
def test_headline_star_verdicts(title,rating):
    assert HSScraper()._extract_rating({'storyLogo':'Elokuva-arvio','title':title}) == rating


def test_literal_rating_wins_over_headline():
    a=preview();a['splitBody']=[{'type':'paragraph','crumbs':[{'content':'Dry Leaf, ohjaus X. 186 min. ★★★'}]}]
    assert HSScraper().parse_html(document(a)).rating_stars == 3


def importer(monkeypatch,asset,titles=('Dry Leaf',)):
    import discovery_importer
    engine=create_engine('sqlite:///:memory:');Base.metadata.create_all(engine)
    db=get_session(engine);db.add(Publication(name='Helsingin Sanomat',short_name='hs'))
    db.add_all([Movie(title=t) for t in titles]);db.commit()
    obj=DiscoveryImporter.__new__(DiscoveryImporter);obj.session=db;obj.source_failures={};obj.scrapers={'hs':HSScraper()}
    obj.meta_scraper=SimpleNamespace(discover_new_reviews=lambda *a:[{'url':asset.get('shareUrl','https://www.hs.fi/example'),'title':'Preview'}])
    monkeypatch.setattr(discovery_importer.requests,'get',lambda *a,**k:SimpleNamespace(text=document(asset),raise_for_status=lambda:None))
    obj.metadata_fetcher=SimpleNamespace(fetch_all_metadata=lambda *a,**k:{})
    return obj


def test_dry_leaf_imports_into_existing_movie(monkeypatch):
    obj=importer(monkeypatch,preview())
    assert obj.import_discovered_reviews('hs') == 1
    row=obj.session.query(Review).one()
    assert row.rating_stars == 4
    assert obj.session.query(Movie).count() == 1
    assert row.movie.title == 'Dry Leaf'
    assert obj.source_failures == {'hs':0}


def test_no_rating_is_not_imported_or_created(monkeypatch):
    a=preview();a['title']='Elokuva-arvio vailla tähtiarviota'
    obj=importer(monkeypatch,a)
    assert obj.import_discovered_reviews('hs') == 0
    assert obj.session.query(Review).count() == 0
    assert obj.session.query(Movie).count() == 1
    assert obj.source_failures == {'hs':0}


@pytest.mark.parametrize('titles,changes',[
    (('Dry Leaf',),{'metaTitle':'Something else','ingress':'Something else'}),
    (('Dry Leaf','Paper Tiger'),{'ingress':'Dry Leaf and Paper Tiger','metaTitle':'Dry Leaf and Paper Tiger'}),
    (('Top Gun',),{'metaTitle':'Top Gun: Maverick','ingress':'Top Gun: Maverick','mainPicture':{}}),
    (('Top Gun',),{'metaTitle':'Top Gun 2','ingress':'Top Gun 2','mainPicture':{}}),
    (('Goat','Goat: Kaikkien aikojen paras'),{'metaTitle':'Goat: Kaikkien aikojen paras','ingress':'Goat: Kaikkien aikojen paras','mainPicture':{}}),
    (('Unknown film',),{}),
    (('Dry Leaf',),{'storyLogo':'Televisioarvio'}),
])
def test_identity_rejects_missing_ambiguous_sequel_and_wrong_type(monkeypatch,titles,changes):
    a={**preview(),**changes};obj=importer(monkeypatch,a,titles)
    # Short/full-name collision may select the unambiguous full movie, never short.
    result=obj.resolve_hs_preview_title(a)
    assert result is None or result == 'Goat: Kaikkien aikojen paras'


def test_caption_and_ingress_can_match_without_meta_title(monkeypatch):
    a=preview();a['metaTitle']='A long editorial headline';obj=importer(monkeypatch,a)
    assert obj.resolve_hs_preview_title(a)=='Dry Leaf'


@pytest.mark.parametrize('sequel',['Top Gun – Maverick','Top Gun - Maverick','Top Gun II','Top Gun Ⅱ'])
def test_unknown_sequel_never_imported_as_original(monkeypatch,sequel):
    a=preview();a.update(metaTitle=sequel,ingress=sequel,mainPicture={})
    obj=importer(monkeypatch,a,('Top Gun',))
    assert obj.import_discovered_reviews('hs') == 0
    assert obj.session.query(Review).count() == 0
    assert obj.session.query(Movie).one().title == 'Top Gun'


def test_resolved_full_title_keeps_existing_movie_id(monkeypatch):
    title='Teräsleidit – kuin viimeistä päivää'
    a=preview();a.update(metaTitle=title,ingress=title,mainPicture={})
    obj=importer(monkeypatch,a,(title,));movie_id=obj.session.query(Movie).one().id
    assert obj.import_discovered_reviews('hs') == 1
    assert obj.session.query(Movie).count() == 1
    assert obj.session.query(Review).one().movie_id == movie_id


@pytest.mark.parametrize('suffix',[' -elokuva',' -elokuvassa',' -dokumentti'])
def test_finnish_film_suffix_is_not_a_sequel(monkeypatch,suffix):
    a=preview();a.update(metaTitle='Dry Leaf'+suffix,ingress='Dry Leaf'+suffix)
    obj=importer(monkeypatch,a)
    assert obj.resolve_hs_preview_title(a)=='Dry Leaf'


@pytest.mark.parametrize('noun',['elokuvaa','sotaelokuvaksi','dokumentin','draamaa','komediaa','trillerin'])
def test_inflected_film_nouns_still_carry_rating(noun):
    assert HSScraper()._extract_rating({'storyLogo':'Elokuva-arvio','title':'Kriitikko kehuu 5 tähden '+noun})==5
