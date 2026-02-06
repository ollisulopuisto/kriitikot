
import pytest
import sys
import os

# Get the directory this test file is in
TEST_DIR = os.path.dirname(__file__)
TEST_DATA_DIR = os.path.join(TEST_DIR, 'test_data')

sys.path.insert(0, os.path.abspath(os.path.join(TEST_DIR, '../src')))
# Import directly from kaleva module since it's disabled from scrapers package
from scrapers.kaleva import KalevaScraper
from scrapers.base import Review

def test_kaleva_scraper_basic():
    """
    Testaa Kaleva-scraperin perustoiminnallisuutta.
    """
    test_file = os.path.join(TEST_DATA_DIR, 'kaleva_review_1.html')
    
    scraper = KalevaScraper()
    review = scraper.parse_file(test_file)
    
    # Varmista että saimme Review-objektin
    assert review is not None, "Kaleva scraper did not return a Review object"
    assert isinstance(review, Review), "Return value is not a Review instance"
    
    # Tarkista kentät
    print("\n=== Kaleva Parsed Review ===")
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

@pytest.mark.skip(reason="Kaleva disabled from scrape_review registry due to paywall")
def test_kaleva_via_general_function():
    test_file = os.path.join(TEST_DATA_DIR, 'kaleva_review_1.html')
    with open(test_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    from scrapers import scrape_review
    review = scrape_review(html_content, source='kaleva', source_url='https://kaleva.fi/test')
    assert review is not None
    assert review.source_publication == "Kaleva"

def test_kaleva_rejects_non_movie_review():
    """
    Testaa että Kaleva-scraper hylkää arvostelut jotka eivät ole elokuvia.
    Esim. Oulu 2026 -tapahtuma-arvio.
    """
    # Minimal HTML without "elokuvat" keyword - simulates event review
    non_movie_html = '''
    <!DOCTYPE html>
    <html lang="fi">
    <head>
        <meta name="zephr:main-keyword" content="oulu 2026">
        <meta name="zephr:keywords" content="oulu 2026, arviot, kulttuuri">
        <title>Arvio: Oulu 2026 käynnistyi viileän luonnon ja viihteen kohtaamisella | Kaleva</title>
    </head>
    <body>
        <h1 class="article__headline">Arvio: Oulu 2026 käynnistyi viileän luonnon ja viihteen kohtaamisella</h1>
        <p class="article__intro">Oulun kulttuuripääkaupunkivuosi alkoi näyttävästi.</p>
        <h2 class="article__lead">Jääsoittimet vakuuttivat yleisön.</h2>
    </body>
    </html>
    '''
    
    scraper = KalevaScraper()
    review = scraper.parse_html(non_movie_html, source_url='https://kaleva.fi/arvio-oulu-2026')
    
    # Should return None for non-movie reviews
    assert review is None, "Scraper should reject non-movie reviews (missing 'elokuvat' keyword)"

