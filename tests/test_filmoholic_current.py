"""Current Film-O-Holic metadata, with legacy markup preserved."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from scrapers.filmoholic import FilmOHolicScraper


def html(rating=3):
    return '<meta property="article:author" content="Jussi Lahtonen"><h1>Pikku kummitus Lapanen keppostelee Valkokangas</h1><script type="application/ld+json">'+json.dumps({
        '@type':'Review','author':{'@type':'Person','name':'Jussi Lahtonen'},
        'itemReviewed':{'@type':'Movie','name':'Pikku kummitus Lapanen keppostelee'},
        'reviewRating':{'@type':'Rating','ratingValue':rating,'bestRating':5}})+'</script>'


def test_current_jsonld_rating_and_article_author():
    review=FilmOHolicScraper().parse_html(html())
    assert (review.movie_title,review.critic_name,review.rating_stars)==('Pikku kummitus Lapanen keppostelee','Jussi Lahtonen',3)


def test_structured_subject_not_an_editorial_headline():
    review=FilmOHolicScraper().parse_html(html().replace('keppostelee Valkokangas</h1>','arvostelun pitkä otsikko</h1>'))
    assert review.movie_title=='Pikku kummitus Lapanen keppostelee'


def test_invalid_or_missing_identity_is_parse_error():
    scraper=FilmOHolicScraper()
    for rating in (None,0,6,3.5,'bad',True):
        assert scraper.parse_html(html(rating)) is None
    assert scraper.parse_html('<h1>A movie</h1><meta itemprop="rating" content="3">') is None
    assert scraper.parse_html('<meta name="author" content="A Critic"><meta itemprop="rating" content="3">') is None
