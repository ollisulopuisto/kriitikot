
import pytest
from scraper import scrape_hs_review

def test_scrape_hs_review_page():
    """
    Testaa yksittäisen HS.fi-arvostelusivun parsimista paikallisesta HTML-tiedostosta.
    """
    test_file = "/Users/dst/Dropbox/koodi/kriitikot/tests/test_data/hs_review_1.html"
    
    scraped_data = scrape_hs_review(test_file)

    assert scraped_data, "No data was scraped."
    # Tämä assertio epäonnistuu tarkoituksella, jotta pytest tulostaa `scraped_data`-sanakirjan sisällön.
    assert False, f"Scraped data: {scraped_data}"
