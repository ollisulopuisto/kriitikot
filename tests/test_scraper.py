
import pytest
import sys
sys.path.insert(0, '/workspaces/kriitikot/src')
from scraper import HSScraper, KSMLScraper, ILScraper, scrape_review, Review


def test_hs_scraper_basic():
    """
    Testaa HS-scraperin perustoiminnallisuutta.
    """
    test_file = "/workspaces/kriitikot/tests/test_data/hs_review_1.html"
    
    scraper = HSScraper()
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
    print(f"URL: {review.source_url}")
    print(f"Review text preview: {review.review_text[:100] if review.review_text else 'N/A'}...")
    
    # Validoi tiedot
    assert review.critic_name == "Pekka Torvinen", f"Expected critic 'Pekka Torvinen', got '{review.critic_name}'"
    assert review.source_publication == "Helsingin Sanomat"
    assert review.rating_stars is not None, "Rating should not be None"
    assert 1 <= review.rating_stars <= 5, f"Rating {review.rating_stars} should be between 1-5"
    assert review.movie_title, "Movie title should not be empty"
    assert "isä osaa" in review.movie_title.lower(), f"Movie title seems wrong: {review.movie_title}"


def test_scrape_review_general_function():
    """
    Testaa yleistä scrape_review()-funktiota.
    """
    test_file = "/workspaces/kriitikot/tests/test_data/hs_review_1.html"
    
    with open(test_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Käytä yleistä funktiota
    review = scrape_review(html_content, source='hs', source_url='https://www.hs.fi/test')
    
    assert review is not None
    assert review.source_url == 'https://www.hs.fi/test'
    assert review.rating_stars is not None


def test_review_to_dict():
    """
    Testaa Review-objektin muunnos sanakirjaksi.
    """
    test_file = "/workspaces/kriitikot/tests/test_data/hs_review_1.html"
    
    scraper = HSScraper()
    review = scraper.parse_file(test_file)
    
    data = review.to_dict()
    
    assert isinstance(data, dict)
    assert 'movie_title' in data
    assert 'critic_name' in data
    assert 'rating_stars' in data
    assert 'source_publication' in data


def test_unknown_source():
    """
    Testaa että tuntematon lähde heittää poikkeuksen.
    """
    with pytest.raises(ValueError, match="Unknown source"):
        scrape_review("<html></html>", source='unknown_site')


def test_ksml_scraper_basic():
    """
    Testaa KSML-scraperin perustoiminnallisuutta.
    """
    test_file = "/workspaces/kriitikot/tests/test_data/ksml_review_1.html"
    
    scraper = KSMLScraper()
    review = scraper.parse_file(test_file)
    
    # Varmista että saimme Review-objektin
    assert review is not None, "KSML scraper did not return a Review object"
    assert isinstance(review, Review), "Return value is not a Review instance"
    
    # Tarkista kentät
    print(f"\n=== KSML Parsed Review ===")
    print(f"Movie: {review.movie_title}")
    print(f"Critic: {review.critic_name}")
    print(f"Rating: {review.rating_stars}/5 stars" if review.rating_stars else "Rating: Not found")
    print(f"Publication: {review.source_publication}")
    
    # Validoi tiedot
    assert review.critic_name == "Jussi Virratvuori", f"Expected critic 'Jussi Virratvuori', got '{review.critic_name}'"
    assert review.source_publication == "Keskisuomalainen"
    assert review.rating_stars == 2, f"Expected rating 2/5, got {review.rating_stars}"
    assert review.movie_title, "Movie title should not be empty"
    assert "isä osaa" in review.movie_title.lower(), f"Movie title seems wrong: {review.movie_title}"


def test_ksml_via_general_function():
    """
    Testaa KSML:n käyttöä yleisen scrape_review()-funktion kautta.
    """
    test_file = "/workspaces/kriitikot/tests/test_data/ksml_review_1.html"
    
    with open(test_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Käytä yleistä funktiota source='ksml'
    review = scrape_review(html_content, source='ksml', source_url='https://www.ksml.fi/paikalliset/8924414')
    
    assert review is not None
    assert review.source_url == 'https://www.ksml.fi/paikalliset/8924414'
    assert review.source_publication == "Keskisuomalainen"
    assert review.rating_stars == 2


def test_il_scraper_basic():
    """
    Testaa IL-scraperin perustoiminnallisuutta.
    """
    test_file = "/workspaces/kriitikot/tests/test_data/il_review_1.html"
    
    scraper = ILScraper()
    review = scraper.parse_file(test_file)
    
    # Varmista että saimme Review-objektin
    assert review is not None, "IL scraper did not return a Review object"
    assert isinstance(review, Review), "Return value is not a Review instance"
    
    # Tarkista kentät
    print(f"\n=== IL Parsed Review ===")
    print(f"Movie: {review.movie_title}")
    print(f"Critic: {review.critic_name}")
    print(f"Rating: {review.rating_stars}/5 stars" if review.rating_stars else "Rating: Not found")
    print(f"Publication: {review.source_publication}")
    
    # Validoi tiedot
    assert review.critic_name == "Juho Rissanen", f"Expected critic 'Juho Rissanen', got '{review.critic_name}'"
    assert review.source_publication == "Iltalehti"
    assert review.rating_stars == 2, f"Expected rating 2/5, got {review.rating_stars}"
    assert review.movie_title, "Movie title should not be empty"
    assert "isä osaa" in review.movie_title.lower(), f"Movie title seems wrong: {review.movie_title}"


def test_il_via_general_function():
    """
    Testaa IL:n käyttöä yleisen scrape_review()-funktion kautta.
    """
    test_file = "/workspaces/kriitikot/tests/test_data/il_review_1.html"
    
    with open(test_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Käytä yleistä funktiota source='il'
    review = scrape_review(html_content, source='il', source_url='https://www.iltalehti.fi/tv-ja-leffat/a/847c8833-444c-433c-aa05-66ab89fe0b94')
    
    assert review is not None
    assert review.source_url == 'https://www.iltalehti.fi/tv-ja-leffat/a/847c8833-444c-433c-aa05-66ab89fe0b94'
    assert review.source_publication == "Iltalehti"
    assert review.rating_stars == 2


