
import pytest
import sys
import os
from bs4 import BeautifulSoup
sys.path.insert(0, '/Users/dst/Dropbox/koodi/kriitikot/src')
from scrapers.kulttuuritoimitus import KulttuuritoimitusScraper, Review

@pytest.fixture
def scraper():
    return KulttuuritoimitusScraper()

def test_extract_title_from_html_infobox(scraper):
    """Test extracting title from the specific infobox structure."""
    with open('tests/test_data/kulttuuritoimitus_repro.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    title = scraper._extract_title(soup)
    assert title == "Teräsleidit – Kuin viimeistä päivää"

def test_extract_movie_name_from_title_with_elokuva_suffix(scraper):
    """Test title extraction when 'elokuva' is part of the title construction."""
    # "Inkerin... - arviossa Teräsleidit-elokuva Kuin viimeistä päivää"
    # This is slightly tricky because "Teräsleidit-elokuva" might be parsed as "Teräsleidit"
    # But currently the scraper might fail on this pattern.
    
    full_title = "Inkerin, Railin, Kertun ja Matin matka oman maailman ympäri on värikäs – arviossa Teräsleidit-elokuva Kuin viimeistä päivää"
    
    # We want to see how it behaves now. The plan is to update it to handle this better if needed,
    # or rely on infobox.
    # If we rely on infobox, this fallback might not be critical, but good to have.
    pass

def test_parse_json_api_uses_content_extraction(scraper):
    """Test that parse_json_api tries to extract title from content HTML."""
    content_html = """
    <div class="et_pb_text_inner">
        <p><b>Correct Movie Title</b></p>
        <ul><li>Ohjaus: Director Name</li></ul>
    </div>
    """
    
    json_data = {
        'title': {'rendered': 'Some Article Heading'},
        'content': {'rendered': content_html},
        'link': 'http://example.com'
    }
    
    review = scraper.parse_json_api(json_data)
    assert review.movie_title == "Correct Movie Title"
    
def test_parse_json_api_fallback(scraper):
    """Test fallback to title if content extraction fails."""
    json_data = {
        'title': {'rendered': 'Arviossa Fallback Title'},
        'content': {'rendered': '<p>Just some text</p>'},
        'link': 'http://example.com'
    }
    
    review = scraper.parse_json_api(json_data)
    assert review.movie_title == "Fallback Title"
