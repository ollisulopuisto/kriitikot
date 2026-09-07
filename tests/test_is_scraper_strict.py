
import pytest
import re
import sys
import os

# Get the directory this test file is in
TEST_DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(TEST_DIR, '../src')))

from scrapers.is_scraper import ISScraper

def test_is_movie_review_strict_cinema():
    """Varmistaa että elokuvateatteriarvostelut hyväksytään."""
    scraper = ISScraper()
    
    good_asset = {
        'tags': [{'key': 'TV-lehti'}, {'key': 'Arviot'}],
        'title': 'The Wizard of the Kremlin -arvio',
        'ingress': 'Poliittinen draama.',
        'splitBody': [
            {'type': 'paragraph', 'crumbs': [{'content': 'The Wizard of the Kremlin, ensi-ilta pe 13.3. elokuvateattereissa. Poliittinen draama ★★★★', 'marks': ['endnote']}]}
        ]
    }
    assert scraper._is_movie_review(good_asset) is True

def test_is_movie_review_strict_streaming_rejected():
    """Varmistaa että suoratoisto/TV-valinnat hylätään."""
    scraper = ISScraper()
    
    bad_asset = {
        'tags': [{'key': 'TV-lehti'}, {'key': 'Arviot'}],
        'title': 'Poor Things -arvio',
        'ingress': 'Emma Stone on ilmiömäinen.',
        'splitBody': [
            {'type': 'paragraph', 'crumbs': [{'content': 'Poor Things (2023), Teema & Fem klo 21.00 keskiviikkona 11.3. sekä Yle Areena & Disney+. Musta komedia ★★★★', 'marks': ['endnote']}]}
        ]
    }
    # Pitäisi nyt palauttaa False, koska endnotessa on "Disney+" ja "klo 21.00" mutta EI "elokuvateattereissa"
    assert scraper._is_movie_review(bad_asset) is False

def test_is_movie_review_streaming_with_theater_accepted():
    """Varmistaa että teatterijulkaisu hyväksytään vaikka suoratoisto mainittaisiin."""
    scraper = ISScraper()
    
    mixed_asset = {
        'tags': [{'key': 'TV-lehti'}, {'key': 'Arviot'}],
        'title': 'Mixed Release -arvio',
        'ingress': 'Tulossa teattereihin ja Disney plussaan.',
        'splitBody': [
            {'type': 'paragraph', 'crumbs': [{'content': 'Mixed Release, ensi-ilta pe 13.3. elokuvateattereissa ja Disney+. ★★★★', 'marks': ['endnote']}]}
        ]
    }
    assert scraper._is_movie_review(mixed_asset) is True

def test_extract_movie_title_clean_comma():
    """Varmistaa että elokuvan nimi siivotaan pilkuista endnotesta otettaessa."""
    scraper = ISScraper()
    
    bad_asset = {
        'splitBody': [
            {'type': 'paragraph', 'crumbs': [{'content': 'Poor Things (2023), Teema & Fem klo 21.00. ★★★★', 'marks': ['endnote']}]}
        ]
    }
    # Pitäisi poimia "Poor Things (2023)" ja siivota pilkun jälkeinen osa pois
    title = scraper._extract_movie_title(bad_asset)
    assert title == "Poor Things (2023)"


def _asset(**overrides):
    """Tyypillinen IS-arvion assetData, jota testit muokkaavat."""
    asset = {
        'tags': [{'key': 'TV-lehti'}, {'key': 'Arviot'}],
        'title': 'Tavallinen otsikko',
        'metaTitle': '',
        'splitBody': [],
    }
    asset.update(overrides)
    return asset


def test_extract_movie_title_from_italics_when_endnote_has_only_genre():
    """Loppurivin lajityyppi ei kelpaa nimeksi, kursiivi kelpaa."""
    scraper = ISScraper()

    asset = _asset(
        title='Suomalaisen historian hämäriin sijoittuva elokuva onnistuu olemaan ihan oikeasti hauska',
        splitBody=[
            {'type': 'paragraph', 'crumbs': [
                {'marks': ['leadin'], 'content': 'Tv-lehti arvioi:'},
                {'marks': [], 'content': ' Suomalaisen historian hämäriin sijoittuva elokuva, joka onnistuu olemaan ihan oikeasti hauska.'},
            ]},
            {'type': 'paragraph', 'crumbs': [
                {'marks': [], 'content': 'Kuulostaa mahdottomalta ajatukselta, mutta Samuli Valkaman ohjaama draamakomedia '},
                {'marks': ['em'], 'content': 'Presidentin kyyditys'},
                {'marks': [], 'content': ' todistaa toisin.'},
            ]},
            {'type': 'paragraph', 'crumbs': [
                {'marks': ['endnote'], 'content': 'Komedia ★★★'},
            ]},
        ],
    )

    assert scraper._extract_movie_title(asset) == 'Presidentin kyyditys'


def test_extract_movie_title_from_endnote_paragraph_with_italic_name():
    """Nimi löytyy, vaikka se olisi endnote-kappaleessa omana kursiivinaan."""
    scraper = ISScraper()

    asset = _asset(splitBody=[
        {'type': 'paragraph', 'crumbs': [
            {'marks': ['em', 'endnote'], 'content': 'Presidentin kyyditys'},
            {'marks': ['endnote'], 'content': ', ensi-ilta pe 5.9. elokuvateattereissa. Komedia ★★★'},
        ]},
    ])

    assert scraper._extract_movie_title(asset) == 'Presidentin kyyditys'


def test_extract_movie_title_endnote_still_wins_over_italics():
    """Loppurivin nimi on edelleen ensisijainen lähde."""
    scraper = ISScraper()

    asset = _asset(splitBody=[
        {'type': 'paragraph', 'crumbs': [
            {'marks': [], 'content': 'Ohjaaja tunnetaan elokuvasta '},
            {'marks': ['em'], 'content': 'Rare Exports'},
            {'marks': [], 'content': '.'},
        ]},
        {'type': 'paragraph', 'crumbs': [
            {'marks': ['endnote'], 'content': 'Sisu 2, ensi-ilta keskiviikkona 22.10. elokuvateattereissa. Toiminta ★★'},
        ]},
    ])

    assert scraper._extract_movie_title(asset) == 'Sisu 2'


def test_extract_movie_title_skips_read_more_italics():
    """"Lue lisää" -nostojen kursiivi ei ole arvioitava elokuva."""
    scraper = ISScraper()

    asset = _asset(
        metaTitle='Presidentin kyyditys -arvio: hauskaa historiaa',
        splitBody=[
            {'type': 'paragraph', 'crumbs': [
                {'marks': ['strong'], 'content': 'Lue lisää: '},
                {'marks': ['em'], 'content': 'Jäätävä poltteen'},
            ]},
            {'type': 'paragraph', 'crumbs': [
                {'marks': ['endnote'], 'content': 'Komedia ★★★'},
            ]},
        ],
    )

    assert scraper._extract_movie_title(asset) == 'Presidentin kyyditys'


@pytest.mark.parametrize('genre', [
    'Komedia', 'Draamakomedia', 'Musta komedia', 'Romanttinen komedia',
    'Toimintaelokuva', 'Dokumentti', 'Psykologinen trilleri',
])
def test_genre_words_are_not_titles(genre):
    scraper = ISScraper()
    assert scraper._looks_like_genre(genre) is True


@pytest.mark.parametrize('title', [
    'Presidentin kyyditys', 'Sisu 2', 'Poor Things (2023)', 'Hytti nro 6',
])
def test_real_titles_are_not_genres(title):
    scraper = ISScraper()
    assert scraper._looks_like_genre(title) is False


def test_rating_found_when_stars_lack_endnote_mark():
    scraper = ISScraper()

    asset = _asset(splitBody=[
        {'type': 'paragraph', 'crumbs': [{'marks': [], 'content': 'Arvion teksti.'}]},
        {'type': 'paragraph', 'crumbs': [{'marks': [], 'content': 'Komedia ★★★★'}]},
    ])

    assert scraper._extract_rating(asset) == 4


def test_parse_html_italic_title_fixture():
    """Koko putki päästä päähän tallennetulla aineistolla."""
    scraper = ISScraper()
    path = os.path.join(TEST_DIR, 'test_data', 'is_review_italic_title.html')
    with open(path, encoding='utf-8') as handle:
        review = scraper.parse_html(handle.read())

    assert review is not None
    assert review.movie_title == 'Presidentin kyyditys'
    assert review.rating_stars == 4


def test_parse_html_sisu_fixture_unchanged():
    """Vanha aineisto parsiutuu edelleen oikein."""
    scraper = ISScraper()
    path = os.path.join(TEST_DIR, 'test_data', 'is_review_1.html')
    with open(path, encoding='utf-8') as handle:
        review = scraper.parse_html(handle.read())

    assert review is not None
    assert review.movie_title == 'Sisu 2'
    assert review.rating_stars == 2
