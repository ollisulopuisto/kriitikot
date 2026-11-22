"""Current Film-O-Holic metadata, with legacy markup preserved."""
import sys,json
import pytest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from scrapers.filmoholic import FilmOHolicScraper


def html(rating=3, author_source='meta'):
    review={'@type':'Review',
        'itemReviewed':{'@type':'Movie','name':'Pikku kummitus Lapanen keppostelee'},
        'reviewRating':{'@type':'Rating','ratingValue':rating,'bestRating':5}}
    if author_source == 'jsonld':
        review['author']={'@type':'Person','name':'Jussi Lahtonen'}
    meta='<meta property="article:author" content="Jussi Lahtonen">' if author_source == 'meta' else ''
    return meta+'<h1>Pikku kummitus Lapanen keppostelee Valkokangas</h1><script type="application/ld+json">'+json.dumps(review)+'</script>'


@pytest.mark.parametrize('author_source',['meta','jsonld'])
def test_current_independent_author_sources(author_source):
    review=FilmOHolicScraper().parse_html(html(author_source=author_source))
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


def test_legacy_meta_author_category_heading_and_rating():
    document='<h1>Sisu 2\nvalkokangas</h1><meta name="author" content="Juha Rosenqvist"><meta itemprop="rating" content="4">'
    review=FilmOHolicScraper().parse_html(document)
    assert (review.movie_title,review.critic_name,review.rating_stars)==('Sisu 2','Juha Rosenqvist',4)


def test_legacy_reviewer_span_without_meta_author():
    document='<h1>Sisu 2\nvalkokangas</h1><span itemprop="reviewer">Juha Rosenqvist</span><meta itemprop="rating" content="4">'
    review=FilmOHolicScraper().parse_html(document)
    assert (review.movie_title,review.critic_name,review.rating_stars)==('Sisu 2','Juha Rosenqvist',4)
