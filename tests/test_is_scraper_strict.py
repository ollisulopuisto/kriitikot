
import pytest
import re
import sys
import os

# Get the directory this test file is in
TEST_DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(TEST_DIR, '../src')))

from scrapers.is_scraper import ISScraper

def test_is_movie_review_strict_cinema():
    """Varmistaa että elokuvateatteriarvostelut hyväksytään."""
    scraper = ISScraper()
    
    good_asset = {
        'tags': [{'key': 'TV-lehti'}, {'key': 'Arviot'}],
        'title': 'The Wizard of the Kremlin -arvio',
        'ingress': 'Poliittinen draama.',
        'splitBody': [
            {'type': 'paragraph', 'crumbs': [{'content': 'The Wizard of the Kremlin, ensi-ilta pe 13.3. elokuvateattereissa. Poliittinen draama ★★★★', 'marks': ['endnote']}]}
        ]
    }
    assert scraper._is_movie_review(good_asset) is True

def test_is_movie_review_strict_streaming_rejected():
    """Varmistaa että suoratoisto/TV-valinnat hylätään."""
    scraper = ISScraper()
    
    bad_asset = {
        'tags': [{'key': 'TV-lehti'}, {'key': 'Arviot'}],
        'title': 'Poor Things -arvio',
        'ingress': 'Emma Stone on ilmiömäinen.',
        'splitBody': [
            {'type': 'paragraph', 'crumbs': [{'content': 'Poor Things (2023), Teema & Fem klo 21.00 keskiviikkona 11.3. sekä Yle Areena & Disney+. Musta komedia ★★★★', 'marks': ['endnote']}]}
        ]
    }
    # Pitäisi nyt palauttaa False, koska endnotessa on "Disney+" ja "klo 21.00" mutta EI "elokuvateattereissa"
    assert scraper._is_movie_review(bad_asset) is False

def test_is_movie_review_streaming_with_theater_accepted():
    """Varmistaa että teatterijulkaisu hyväksytään vaikka suoratoisto mainittaisiin."""
    scraper = ISScraper()
    
    mixed_asset = {
        'tags': [{'key': 'TV-lehti'}, {'key': 'Arviot'}],
        'title': 'Mixed Release -arvio',
        'ingress': 'Tulossa teattereihin ja Disney plussaan.',
        'splitBody': [
            {'type': 'paragraph', 'crumbs': [{'content': 'Mixed Release, ensi-ilta pe 13.3. elokuvateattereissa ja Disney+. ★★★★', 'marks': ['endnote']}]}
        ]
    }
    assert scraper._is_movie_review(mixed_asset) is True

def test_extract_movie_title_clean_comma():
    """Varmistaa että elokuvan nimi siivotaan pilkuista endnotesta otettaessa."""
    scraper = ISScraper()
    
    bad_asset = {
        'splitBody': [
            {'type': 'paragraph', 'crumbs': [{'content': 'Poor Things (2023), Teema & Fem klo 21.00. ★★★★', 'marks': ['endnote']}]}
        ]
    }
    # Pitäisi poimia "Poor Things (2023)" ja siivota pilkun jälkeinen osa pois
    title = scraper._extract_movie_title(bad_asset)
    assert title == "Poor Things (2023)"
