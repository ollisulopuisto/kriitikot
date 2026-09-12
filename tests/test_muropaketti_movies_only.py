"""Muropaketin peliarvostelut eivät saa päätyä elokuvakantaan."""

import os
import sys

TEST_DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(TEST_DIR, '../src')))

from bs4 import BeautifulSoup

from discovery import CategoryCrawler
from scrapers import MuropakettiScraper


CATEGORY_HTML = """
<html><body>
<a href="https://muropaketti.com/elokuvat/elokuva-arvostelut/arvostelu-testileffa/">
    <span class="category-name">Arvostelu</span>Testileffa on hyvä
</a>
<a href="https://muropaketti.com/pelit/peliarvostelut/arvostelu-star-wars-zero-companya-on-helppo-suositella-etenkin-xcomin-faneille/">
    <span class="category-name">Arvostelu</span>Star Wars: Zero Companya on helppo suositella
</a>
<a href="https://muropaketti.com/tekniikka/nayttopaate/arvostelu-testinaytto/">
    <span class="category-name">Arvio</span>Testinäyttö
</a>
</body></html>
"""

GAME_REVIEW_HTML = """
<html><head><meta name="author" content="Testikriitikko" /></head>
<body><h1>Arvostelu  Star Wars: Zero Company</h1>
<div class="entry-content">
<p>Peliarvostelussa on vuoropohjainen taktiikkapeli, joka lainaa XCOM-sarjalta reilusti.</p>
<img src="https://muropaketti.com/kuvat/arvostelu-tahdet-4.png" alt="Arvosana: 4/5" />
</div></body></html>
"""


def test_discovery_skips_game_reviews():
    soup = BeautifulSoup(CATEGORY_HTML, 'html.parser')
    reviews = CategoryCrawler()._find_muropaketti_reviews(soup, limit=10)

    urls = [r['url'] for r in reviews]
    assert urls == ['https://muropaketti.com/elokuvat/elokuva-arvostelut/arvostelu-testileffa/']


def test_scraper_rejects_game_review_url():
    url = ('https://muropaketti.com/pelit/peliarvostelut/'
           'arvostelu-star-wars-zero-companya-on-helppo-suositella-etenkin-xcomin-faneille/')

    assert MuropakettiScraper().parse_html(GAME_REVIEW_HTML, url) is None
