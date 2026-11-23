"""Paywalled KSML previews remain unimported, but have a visible non-failing outcome."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from discovery_importer import DiscoveryImporter
from models import Base, Critic, Movie, Publication, Review, get_session
from scrapers.ksml import KSMLScraper


def page(access='false', rating='', title='A Film', author='A Critic'):
    return ('<script type="application/ld+json">'
            '{"@type":"NewsArticle","isAccessibleForFree":' + access + '}</script>'
            f'<p class="diks-storyline__lead-paragraph">{title}</p>'
            f'<meta name="author" content="{author}">{rating}')


def test_explicit_paywalled_unrated_preview_is_excluded():
    assert KSMLScraper().exclusion_reason(page()) == 'paywalled_unrated_preview'


@pytest.mark.parametrize('html', [
    page(access='true'), page(access='"false"'), page(access='null'),
    page(rating='<span aria-label="Arvosana: 3/5 tähteä"></span>'),
    page(rating='<span aria-label="Arvosana: 0/5 tähteä"></span>'),
    page(rating='<p>★★★★</p>'),
    page(rating='<p>0/5</p>'),
    page(title=''), page(author=''), page(author='Unknown'),
    page(author='Keskisuomalainen'), page(author='https://example.test/author'),
    '<script type="application/ld+json">{broken}</script>', 'Broken response',
])
def test_only_complete_explicitly_paywalled_previews_are_excluded(html):
    assert KSMLScraper().exclusion_reason(html) is None


@pytest.mark.parametrize('html,failures,excluded', [
    (page(), 0, 1), (page(access='true'), 1, 0), ('Broken response', 1, 0),
    (page(title=''), 1, 0), (page(author='Unknown'), 1, 0),
])
def test_importer_keeps_preview_out_of_db_and_counts_outcome(monkeypatch, capsys, html, failures, excluded):
    import discovery_importer
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db = get_session(engine)
    db.add(Publication(name='Keskisuomalainen', short_name='ksml'))
    db.commit()
    importer = DiscoveryImporter.__new__(DiscoveryImporter)
    importer.session = db
    importer.source_failures = {}
    importer.scrapers = {'ksml': KSMLScraper()}
    importer.meta_scraper = SimpleNamespace(discover_new_reviews=lambda *a: [
        {'title': 'Candidate', 'url': 'https://www.ksml.fi/paikalliset/123'}])
    importer.get_or_create_movie = MagicMock(side_effect=AssertionError('No movie writes'))
    importer.get_or_create_critic = MagicMock(side_effect=AssertionError('No critic writes'))
    monkeypatch.setattr(discovery_importer.requests, 'get', lambda *a, **k:
        SimpleNamespace(text=html, raise_for_status=lambda: None))
    assert importer.import_discovered_reviews('ksml') == 0
    assert importer.source_failures == {'ksml': failures}
    assert importer.source_exclusions['ksml'] == ({'paywalled_unrated_preview': 1} if excluded else {})
    if excluded:
        assert 'paywalled_unrated_preview: 1' in capsys.readouterr().out
    importer.get_or_create_movie.assert_not_called()
    importer.get_or_create_critic.assert_not_called()
    assert db.query(Movie).count() == db.query(Critic).count() == db.query(Review).count() == 0
    db.close()
