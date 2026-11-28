"""Explicit series subject is not a broken movie parser or a film identity."""
from pathlib import Path
from unittest.mock import MagicMock
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine

from scrapers.muropaketti import MuropakettiScraper
from discovery_importer import DiscoveryImporter
from models import Base, Publication, Movie, Critic, Review, get_session

FIXTURE = Path(__file__).parent / 'fixtures/muropaketti-tv-excerpt.html'


def test_live_series_excerpt_is_excluded():
    assert MuropakettiScraper().exclusion_reason(FIXTURE.read_text()) == 'tv_series_review'


@pytest.mark.parametrize('html', [
    '<article><h1>A film</h1><p>A tv-sarja is mentioned elsewhere.</p></article>',
    '<article><h1>A film</h1><div class="content__excerpt">A film compares with a tv-sarja.</div></article>',
    '<article><h1>Unknown</h1><div class="content__excerpt">Preview only.</div></article>',
    '<html>Broken page</html>',
    '<article class="content__wrapper"><h1>Different film</h1><div class="content__excerpt">Another title -tv-sarja is reviewed.</div></article>',
    '<article class="content__wrapper"><h1>A title</h1><div class="content__excerpt">A title -tv-sarja is reviewed.</div><p><strong>A title</strong> Ensi-ilta: today</p></article>',
])
def test_missing_or_incidental_series_evidence_is_not_excluded(html):
    assert MuropakettiScraper().exclusion_reason(html) is None


def test_importer_excludes_series_without_creating_film_or_hiding_parser_failure(monkeypatch):
    import discovery_importer
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db = get_session(engine)
    db.add(Publication(name='Muropaketti', short_name='muropaketti'))
    db.commit()
    importer = DiscoveryImporter.__new__(DiscoveryImporter)
    importer.session = db
    importer.source_failures = {}
    importer.scrapers = {'muropaketti': MuropakettiScraper()}
    importer.meta_scraper = SimpleNamespace(discover_new_reviews=lambda *a: [
        {'title': 'Candidate', 'url': 'https://muropaketti.com/elokuvat/elokuva-arvostelut/candidate/'}])
    importer.get_or_create_movie = MagicMock(side_effect=AssertionError('No movie writes'))
    importer.get_or_create_critic = MagicMock(side_effect=AssertionError('No critic writes'))
    for html, failures in [(FIXTURE.read_text(), 0), (tag_page(['sarjat']), 0), ('Broken page', 1)]:
        monkeypatch.setattr(discovery_importer.requests, 'get', lambda *a, **k:
            SimpleNamespace(text=html, raise_for_status=lambda: None))
        assert importer.import_discovered_reviews('muropaketti') == 0
        assert importer.source_failures == {'muropaketti': failures}
    assert db.query(Movie).count() == db.query(Critic).count() == db.query(Review).count() == 0


@pytest.mark.parametrize('marker', ['tv-sarja', 'minisarja', 'televisiosarja'])
def test_series_markers_are_general_not_a_title_exception(marker):
    html = ('<article class="content__wrapper"><h1>Arvio: Unrelated New Title</h1>'
            '<div class="content__excerpt">Unrelated New Title -' + marker +
            ' kertoo etsivistä.</div></article>')
    assert MuropakettiScraper().exclusion_reason(html) == 'tv_series_review'


def test_franchise_film_lead_without_facts_is_not_silently_excluded():
    html = ('<article class="content__wrapper"><h1>Scream saa uuden osan</h1>'
            '<div class="content__excerpt">Scream -sarja saa uuden osan.</div></article>')
    assert MuropakettiScraper().exclusion_reason(html) is None


def tag_page(tags, facts='', lead=''):
    return ('<article class="content__wrapper"><h1>A subject</h1>' + lead +
            '<ul class="content__tag-list">' + ''.join(
                '<li class="content__tag-list_item"><a href="/avainsana/example/">' + tag + '</a></li>'
                for tag in tags) + '</ul>' + facts + '</article>')


def test_explicit_article_series_tag_without_lead_is_excluded():
    assert MuropakettiScraper().exclusion_reason(tag_page(['Prime Video', 'sarjat'])) == 'tv_series_review'


@pytest.mark.parametrize('html', [
    '<nav><a href="/avainsana/netti-ja-tv-sarjat/">sarjat</a></nav>' + tag_page(['Elokuvat']),
    tag_page(['tv-sarjat', 'sarjatuotanto']),
    tag_page(['sarjat'], '<p><strong>A film</strong> Ensi-ilta: today</p>'),
    '<ul class="content__tag-list"><li class="content__tag-list_item"><a>sarjat</a></li></ul>' + tag_page([]),
])
def test_tags_outside_article_partial_tags_and_film_facts_do_not_exclude(html):
    assert MuropakettiScraper().exclusion_reason(html) is None
