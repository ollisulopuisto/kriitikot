from pathlib import Path
import pytest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('rating', range(1, 6))
def test_server_stars_match_the_lazy_contract(rating):
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=True)
    html = env.get_template('_rating_stars.html').render(review={'rating_stars': rating})
    stars = BeautifulSoup(html, 'html.parser').select_one('.rating-stars')
    assert len(stars.select('.rating-star')) == 5
    assert len(stars.select('.rating-star-empty')) == 5 - rating
    assert stars.text == '★' * rating
    assert stars['aria-label'] == f'{rating}/5 tähteä'
    assert stars['role'] == 'img'
    assert all(s['aria-hidden'] == 'true' for s in stars.select('.rating-star'))

def test_all_server_pills_use_shared_slots():
    for name in ('_movie_row.html', '_movie_card.html'):
        assert (ROOT / 'templates' / name).read_text(encoding='utf-8').count("include '_rating_stars.html'") == 2

def test_generated_assets_match_source():
    for name in ('app.js', 'css/base.css', 'css/table.css', 'css/cards.css'):
        assert (ROOT / 'static' / name).read_bytes() == (ROOT / 'docs/static' / name).read_bytes()

def test_requested_color_scale():
    from test_rating_colour_contrast import _tokens
    tokens = _tokens()
    assert [tokens[f'--star-{n}'] for n in range(1, 6)] == [
        '#b91c1c', '#a83a12', '#ffd60a', '#38bdf8', '#22c55e']
