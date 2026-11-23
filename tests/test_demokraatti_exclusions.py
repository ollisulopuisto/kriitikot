"""Only positively identified festival features are harmless non-review candidates."""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from discovery_importer import DiscoveryImporter
from models import Base, Critic, Movie, Publication, Review, get_session
from scrapers.demokraatti import DemokraattiScraper

FEATURE = {
    'title': 'Rakkautta & anarkiaa alkaa – kriitikko nimeää yhden lemmikin',
    'content': '<p>Rakkautta &amp; anarkiaa täyttää taas pääkaupungin valkokankaat, '
               '38 vuotta perustamisensa jälkeen.</p><p>Festivaalin ohjelmistossa '
               'on laaja otos nykyelokuvaa.</p>',
    'categories': {'nodes': [{'name': 'Elokuva'}]},
}


def page(post):
    data = {'props': {'pageProps': {'dehydratedState': {'queries': [{
        'queryKey': ['singlePostMain', 'festival-feature'],
        'state': {'data': {'singlePost': post}},
    }]}}}}
    return '<script id="__NEXT_DATA__">' + json.dumps(data) + '</script>'


def test_festival_feature_has_positive_exclusion_evidence():
    scraper = DemokraattiScraper()
    assert scraper.exclusion_reason(page(FEATURE)) == 'festival_feature'
    assert scraper.parse_html(page(FEATURE)) is None


@pytest.mark.parametrize('change', ['headline', 'body', 'review_headline', 'infobox', 'stars'])
def test_missing_or_conflicting_evidence_remains_unresolved(change):
    post = copy.deepcopy(FEATURE)
    if change == 'headline':
        post['title'] = 'A movie article'
    elif change == 'body':
        post['content'] = '<p>Preview text only.</p>'
    elif change == 'review_headline':
        post['title'] = 'Arvio: ' + post['title']
    elif change == 'infobox':
        post['content'] += '<div class="well"><strong>ELOKUVA</strong><em>A Film</em></div>'
    else:
        post['content'] += '<p>★★★★</p>'
    assert DemokraattiScraper().exclusion_reason(page(post)) is None


@pytest.mark.parametrize('html', ['Broken page', '<script id="__NEXT_DATA__">{}</script>'])
def test_missing_structured_article_is_not_excluded(html):
    assert DemokraattiScraper().exclusion_reason(html) is None


@pytest.mark.parametrize('html,failures', [(page(FEATURE), {'demokraatti': 0}), ('Broken page', {'demokraatti': 1}),
    (page({'title': 'Arvio: A Film', 'content': '<p>Preview only</p>'}), {'demokraatti': 1})])
def test_importer_skips_only_classified_features_without_creating_rows(monkeypatch, html, failures):
    import discovery_importer
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db = get_session(engine)
    db.add(Publication(name='Demokraatti', short_name='demokraatti'))
    db.commit()
    importer = DiscoveryImporter.__new__(DiscoveryImporter)
    importer.session = db
    importer.source_failures = {}
    importer.scrapers = {'demokraatti': DemokraattiScraper()}
    importer.meta_scraper = SimpleNamespace(discover_new_reviews=lambda *a: [
        {'title': 'Candidate', 'url': 'https://demokraatti.fi/feature/'}])
    importer.get_or_create_movie = MagicMock(side_effect=AssertionError('No movie writes'))
    importer.get_or_create_critic = MagicMock(side_effect=AssertionError('No critic writes'))
    monkeypatch.setattr(discovery_importer.requests, 'get', lambda *a, **k:
        SimpleNamespace(text=html, raise_for_status=lambda: None))
    assert importer.import_discovered_reviews('demokraatti') == 0
    assert importer.source_failures == failures
    importer.get_or_create_movie.assert_not_called()
    importer.get_or_create_critic.assert_not_called()
    assert db.query(Movie).count() == db.query(Critic).count() == db.query(Review).count() == 0
    db.close()
