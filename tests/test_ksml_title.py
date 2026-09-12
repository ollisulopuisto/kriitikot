"""KSML:n otsikkopoiminnan regressiotestit."""

import os
import sys

TEST_DIR = os.path.dirname(__file__)
TEST_DATA_DIR = os.path.join(TEST_DIR, 'test_data')

sys.path.insert(0, os.path.abspath(os.path.join(TEST_DIR, '../src')))

from scrapers import KSMLScraper


def _parse(filename, source_url=None):
    with open(os.path.join(TEST_DATA_DIR, filename), encoding='utf-8') as f:
        html = f.read()
    return KSMLScraper().parse_html(html, source_url)


def test_title_comes_from_storyline_not_lead_sentence():
    """Ingressilause ei kelpaa elokuvan nimeksi."""
    review = _parse('ksml_review_dual_title.html', 'https://www.ksml.fi/paikalliset/9781807')

    assert review is not None
    assert review.movie_title == 'The Visitor'
    assert review.critic_name == 'Olli-Matti Oinonen'
    assert review.rating_stars == 3


def test_finnish_title_still_parses():
    """Yksiosainen kotimainen nimi säilyy ennallaan."""
    review = _parse('ksml_review_1.html')

    assert review is not None
    assert review.movie_title == 'Kyllä isä osaa Lapissa'
