import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from scrapers.demokraatti import DemokraattiScraper
from scrapers.base import Review

def test_demokraatti_scraper_basic():
    """
    Testaa Demokraatti-scraperin perustoiminnallisuutta.
    """
    test_file = "tests/test_data/demokraatti_review_1.html"
    
    scraper = DemokraattiScraper()
    review = scraper.parse_file(test_file)
    
    # Varmista että saimme Review-objektin
    assert review is not None, "Scraper did not return a Review object"
    assert isinstance(review, Review), "Return value is not a Review instance"
    
    # Tarkista kentät
    print(f"\n=== Parsed Review ===")
    print(f"Movie: {review.movie_title}")
    print(f"Critic: {review.critic_name}")
    print(f"Rating: {review.rating_stars}/5 stars")
    print(f"Publication: {review.source_publication}")
    
    # Validoi tiedot
    assert review.critic_name == "Rolf Bamberg", f"Expected critic 'Rolf Bamberg', got '{review.critic_name}'"
    assert review.source_publication == "Demokraatti"
    assert review.rating_stars == 2, f"Expected rating 2/5, got {review.rating_stars}"
    
    # Title validation
    # Title should be extracted from the infobox
    assert review.movie_title == "Kalevala: Kullervo"
    
    # Review text should be present
    assert review.review_text is not None
    assert len(review.review_text) > 100

def test_is_review_logic():
    """
    Testaa että scraper tunnistaa arvostelut oikein.
    """
    scraper = DemokraattiScraper()
    
    # Mock data structure that represents a review
    review_data = {
        'title': 'Arvio: Elokuva X',
        'categories': {'nodes': [{'name': 'Elokuva'}]}
    }
    assert scraper._is_movie_review(review_data) is True
    
    # Mock data for non-review
    news_data = {
        'title': 'Uutinen: Jotain tapahtui',
        'categories': {'nodes': [{'name': 'Uutiset'}]}
    }
    assert scraper._is_movie_review(news_data) is False
