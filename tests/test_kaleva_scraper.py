
import pytest
import sys
sys.path.insert(0, '/Users/dst/Dropbox/koodi/kriitikot/src')
from scrapers import KalevaScraper, scrape_review
from scrapers.base import Review

def test_kaleva_scraper_basic():
    """
    Testaa Kaleva-scraperin perustoiminnallisuutta.
    """
    test_file = "/Users/dst/Dropbox/koodi/kriitikot/tests/test_data/kaleva_review_1.html"
    
    scraper = KalevaScraper()
    review = scraper.parse_file(test_file)
    
    # Varmista että saimme Review-objektin
    assert review is not None, "Kaleva scraper did not return a Review object"
    assert isinstance(review, Review), "Return value is not a Review instance"
    
    # Tarkista kentät
    print(f"\n=== Kaleva Parsed Review ===")
    print(f"Movie: {review.movie_title}")
    print(f"Critic: {review.critic_name}")
    print(f"Rating: {review.rating_stars}/5 stars" if review.rating_stars else "Rating: Not found")
    print(f"Publication: {review.source_publication}")
    print(f"Review Text: {review.review_text[:100] if review.review_text else 'None'}...")
    
    # Validoi tiedot
    # Author: Anssi Juntto (from inspecting html)
    # Title: Should be refined from article intro
    
    # Critic
    assert review.critic_name == "Anssi Juntto"
    assert review.source_publication == "Kaleva"
    
    # Rating
    assert review.rating_stars is not None
    
    # Refined Title Check
    assert "Teräsleidit – kuin viimeistä päivää" in review.movie_title
    # Ensure it doesn't contain the headline "Arvio: ..." prefix if it fell back,
    # but specifically check that it picked the name from the intro if possible.
    # The full intro start was "Teräsleidit – kuin viimeistä päivää, Suomi 2025"
    # Our logic splits by comma.
    assert review.movie_title == "Teräsleidit – kuin viimeistä päivää"

    # Review Text
    assert review.review_text
    assert "Väärä diagnoosi" in review.review_text

def test_kaleva_via_general_function():
    test_file = "/Users/dst/Dropbox/koodi/kriitikot/tests/test_data/kaleva_review_1.html"
    with open(test_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    review = scrape_review(html_content, source='kaleva', source_url='https://kaleva.fi/test')
    assert review is not None
    assert review.source_publication == "Kaleva"
