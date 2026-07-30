"""Testit arvosanajakauman (sparkline) renderöinnille.

Palkin korkeus kertoo muodon (onko mielipide jakautunut), väri kertoo
arvosanan. Väriluokan on vastattava palkin paikkaa, muuten kaavio valehtelee.
"""

import os
import sys

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import app


def render_row(dist, title="Testielokuva"):
    """Renderöi _movie_row.html annetulla jakaumalla."""
    with app.app_context():
        html = app.jinja_env.get_template('_movie_row.html').render(
            movie_title=title,
            critics_reviews={},
            all_critics=[],
            poster_urls={},
            letterboxd_urls={},
            nytleffaan_urls={},
            movie_review_counts={},
            movie_rating_distributions={title: dist},
        )
    return BeautifulSoup(html, 'html.parser')


def spark_bars(soup):
    return soup.select('.movie-sparkline .spark-bar')


def test_each_bar_gets_matching_colour_class():
    """Palkin n väriluokan on oltava spark-bar-n."""
    bars = spark_bars(render_row([1, 2, 3, 2, 1]))

    assert len(bars) == 5
    for i, bar in enumerate(bars, start=1):
        assert f'spark-bar-{i}' in bar['class'], f"palkki {i} sai väärän väriluokan: {bar['class']}"


def test_tallest_bar_is_full_height():
    """Korkeus suhteutetaan suurimpaan, jotta muoto on vertailukelpoinen."""
    bars = spark_bars(render_row([0, 0, 4, 2, 0]))

    heights = [bar.get('style', '') for bar in bars]
    assert 'height: 100.0%' in heights[2] or 'height: 100%' in heights[2]
    assert 'height: 50.0%' in heights[3] or 'height: 50%' in heights[3]


def test_shape_is_comparable_regardless_of_volume():
    """Yksi 4 tähden arvio ja neljä 4 tähden arviota antavat saman muodon.

    Tämä on tarkoituksellista: määrä näkyy erillisestä arvostelulaskurista.
    """
    few = [bar.get('style') for bar in spark_bars(render_row([0, 0, 0, 1, 0]))]
    many = [bar.get('style') for bar in spark_bars(render_row([0, 0, 0, 4, 0]))]

    assert few == many


def test_empty_ratings_are_marked():
    """Nollapalkit merkitään haaleiksi, jottei 1px viiva näytä osumalta."""
    bars = spark_bars(render_row([0, 3, 0, 1, 0]))

    empty = [i for i, bar in enumerate(bars, start=1) if 'spark-bar--empty' in bar['class']]
    assert empty == [1, 3, 5]


def test_divided_opinion_renders_multiple_tall_bars():
    """Jakautunut mielipide -> useita korkeita palkkeja."""
    bars = spark_bars(render_row([3, 0, 0, 0, 3]))

    assert 'spark-bar--empty' not in bars[0]['class']
    assert 'spark-bar--empty' not in bars[4]['class']
    assert 'height: 100.0%' in bars[0]['style']
    assert 'height: 100.0%' in bars[4]['style']


def test_sparkline_has_accessible_label():
    """Kaavio on role=img ja sen selite kertoo jakauman myös ilman hoveria."""
    soup = render_row([0, 1, 3, 2, 0])
    sparkline = soup.select_one('.movie-sparkline')

    assert sparkline['role'] == 'img'
    label = sparkline['aria-label']
    for fragment in ('1★ 0', '2★ 1', '3★ 3', '4★ 2', '5★ 0'):
        assert fragment in label
    assert sparkline['title'] == label


def test_sparkline_omitted_when_no_ratings():
    """Ilman arvosanoja kaaviota ei piirretä lainkaan."""
    assert spark_bars(render_row([0, 0, 0, 0, 0])) == []


@pytest.mark.parametrize("template", ['_movie_row.html', '_movie_card.html'])
def test_both_templates_use_same_bar_markup(template):
    """Rivi- ja korttinäkymän sparklinen on oltava samanlainen."""
    title = "Testielokuva"
    with app.app_context():
        html = app.jinja_env.get_template(template).render(
            movie_title=title,
            critics_reviews={},
            all_critics=[],
            poster_urls={},
            letterboxd_urls={},
            nytleffaan_urls={},
            movie_review_counts={},
            movie_rating_distributions={title: [1, 0, 2, 0, 1]},
        )
    soup = BeautifulSoup(html, 'html.parser')
    bars = soup.select('.movie-sparkline .spark-bar')

    assert len(bars) == 5
    for i, bar in enumerate(bars, start=1):
        assert f'spark-bar-{i}' in bar['class']
    empty = [i for i, bar in enumerate(bars, start=1) if 'spark-bar--empty' in bar['class']]
    assert empty == [2, 4]
