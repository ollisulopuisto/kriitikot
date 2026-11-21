"""Rating hover text in both server-rendered responsive trees."""
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('template', ['_movie_card.html', '_movie_row.html'])
@pytest.mark.parametrize('rating', range(1, 6))
@pytest.mark.parametrize('excerpt', ['', 'A <film> & "review"'])
def test_rating_title_preserves_publication_and_excerpt(template, rating, excerpt):
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=True)
    env.filters['publication_name'] = str
    review = {'rating_stars': rating, 'source_url': 'https://example.com/review',
                  'review_text': excerpt,
                  'publication': {'short_name': 'hs', 'name': 'A "publication"'}}
    html = env.get_template(template).render(
        movie_title='Test', critics_reviews={'Test': [review]},
        all_critics=[{'name': 'Test', 'id': 1}], poster_urls={},
        nytleffaan_urls={}, letterboxd_urls={}, movie_review_counts={},
        movie_rating_distributions={})
    pill = BeautifulSoup(html, 'html.parser').select_one('a.rating-pill')
    assert pill['title'] == (
        f'A "publication": {rating}/5 tähteä. {excerpt or "Lue arvostelu"}...')
    assert pill.select_one('film') is None
    assert pill.select_one('.rating-stars')['aria-label'] == f'{rating}/5 tähteä'
