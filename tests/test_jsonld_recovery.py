"""Real scraper helpers must recover past broken unrelated metadata."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scrapers.base import BaseScraper


@pytest.mark.parametrize("prefix", [
    '<script type="application/ld+json">{broken</script>',
    '<script type="application/ld+json">{"@type":"WebSite","name":"Publisher"}</script>',
])
def test_later_review_survives_unrelated_or_invalid_jsonld(prefix):
    scraper = BaseScraper(publication_name="Fixture")
    html = prefix + '''<script type="application/ld+json">
    {"@graph":[{"@type":"Review","headline":"Ääni ja kuva","author":{"name":"Test Critic"}}]}
    </script>'''
    review = scraper.extract_jsonld(scraper.get_soup(html))
    assert review["headline"] == "Ääni ja kuva"
    assert review["author"]["name"] == "Test Critic"


def test_missing_review_metadata_returns_none():
    scraper = BaseScraper(publication_name="Fixture")
    assert scraper.extract_jsonld(scraper.get_soup('<script type="application/ld+json">null</script>')) is None
