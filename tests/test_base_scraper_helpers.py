"""Testit BaseScraperin jaetuille poimintaapureille."""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from scrapers.base import BaseScraper


@pytest.fixture
def scraper():
    return BaseScraper(publication_name="Test")


def soup_of(scraper, html):
    return scraper.get_soup(html)


# --- count_stars ---------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("★★★★", 4),
    ("⭐⭐", 2),
    ("Arvio: ★★★★★", 5),
    ("★★★★★★★", 5),          # rajataan maksimiin
    ("ei tähtiä", None),
    ("", None),
    (None, None),
])
def test_count_stars(scraper, text, expected):
    assert scraper.count_stars(text) == expected


# --- parse_rating --------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("IL-arvio: ★★★", 3),
    ("Arvosana: 4/5", 4),
    ("Elokuva sai 3 tähteä", 3),
    ("neljän tähden elokuva", 4),
    ("Viisi tähteä tälle!", 5),
    ("Kolme tähteä", 3),
    ("kahden tähden arvoinen", 2),
    ("sai 5 tähtiä", 5),
    ("ei arvosanaa lainkaan", None),
    ("", None),
])
def test_parse_rating(scraper, text, expected):
    assert scraper.parse_rating(text) == expected


def test_parse_rating_ignores_taha_words(scraper):
    """'tähän' ei ole tähti-sana, vaikka alkaa samoin."""
    assert scraper.parse_rating("neljä syytä tähän elokuvaan") is None


def test_parse_rating_requires_star_word_for_numerals(scraper):
    """Pelkkä lukusana ilman tähti-sanaa ei ole arvosana."""
    assert scraper.parse_rating("neljä ystävää lähti matkalle") is None


def test_parse_rating_prefers_star_glyphs(scraper):
    """Tähtisymbolit voittavat tekstissä esiintyvät numerot."""
    assert scraper.parse_rating("★★ – mutta 5/5 olisi liikaa") == 2


# --- extract_jsonld ------------------------------------------------------

def test_extract_jsonld_plain_dict(scraper):
    html = '<script type="application/ld+json">{"@type": "NewsArticle", "headline": "X"}</script>'
    result = scraper.extract_jsonld(soup_of(scraper, html))
    assert result['headline'] == 'X'


def test_extract_jsonld_list_form(scraper):
    html = '''<script type="application/ld+json">
    [{"@type": "WebPage"}, {"@type": "Review", "headline": "Y"}]</script>'''
    result = scraper.extract_jsonld(soup_of(scraper, html))
    assert result['headline'] == 'Y'


def test_extract_jsonld_graph_form(scraper):
    html = '''<script type="application/ld+json">
    {"@graph": [{"@type": "Person"}, {"@type": "Article", "headline": "Z"}]}</script>'''
    result = scraper.extract_jsonld(soup_of(scraper, html))
    assert result['headline'] == 'Z'


def test_extract_jsonld_type_list(scraper):
    """@type voi olla lista."""
    html = '<script type="application/ld+json">{"@type": ["Article", "Thing"], "headline": "Q"}</script>'
    assert scraper.extract_jsonld(soup_of(scraper, html))['headline'] == 'Q'


def test_extract_jsonld_skips_invalid_json(scraper):
    html = ('<script type="application/ld+json">{ rikki json </script>'
            '<script type="application/ld+json">{"@type": "Article", "headline": "OK"}</script>')
    assert scraper.extract_jsonld(soup_of(scraper, html))['headline'] == 'OK'


def test_extract_jsonld_returns_none_when_absent(scraper):
    assert scraper.extract_jsonld(soup_of(scraper, '<html></html>')) is None


# --- extract_author ------------------------------------------------------

def test_extract_author_from_article_author_meta(scraper):
    html = '<meta property="article:author" content="Matti Meikäläinen">'
    assert scraper.extract_author(soup_of(scraper, html)) == 'Matti Meikäläinen'


def test_extract_author_from_meta_name(scraper):
    html = '<meta name="author" content="Liisa Virtanen">'
    assert scraper.extract_author(soup_of(scraper, html)) == 'Liisa Virtanen'


def test_extract_author_from_jsonld_dict(scraper):
    ld = {'author': {'name': 'Kalle Kirjoittaja'}}
    assert scraper.extract_author(soup_of(scraper, ''), ld) == 'Kalle Kirjoittaja'


def test_extract_author_from_jsonld_list(scraper):
    ld = {'author': [{'name': 'Ensimmäinen Nimi'}, {'name': 'Toinen'}]}
    assert scraper.extract_author(soup_of(scraper, ''), ld) == 'Ensimmäinen Nimi'


def test_extract_author_from_jsonld_string(scraper):
    assert scraper.extract_author(soup_of(scraper, ''), {'author': 'Suora Nimi'}) == 'Suora Nimi'


def test_extract_author_excludes_publication_name(scraper):
    """Julkaisun oma nimi ei kelpaa kriitikoksi — siirrytään seuraavaan lähteeseen."""
    html = ('<meta property="article:author" content="Turun Sanomat">'
            '<meta name="author" content="Oikea Kriitikko">')
    result = scraper.extract_author(soup_of(scraper, html), exclude=('Turun Sanomat', 'TS'))
    assert result == 'Oikea Kriitikko'


def test_extract_author_returns_none_when_absent(scraper):
    assert scraper.extract_author(soup_of(scraper, '<html></html>')) is None


# --- meta_description ----------------------------------------------------

def test_meta_description_prefers_og(scraper):
    html = ('<meta property="og:description" content="OG-teksti">'
            '<meta name="description" content="Tavallinen">')
    assert scraper.meta_description(soup_of(scraper, html)) == 'OG-teksti'


def test_meta_description_falls_back_to_name(scraper):
    html = '<meta name="description" content="Tavallinen">'
    assert scraper.meta_description(soup_of(scraper, html)) == 'Tavallinen'


def test_meta_description_none_when_absent(scraper):
    assert scraper.meta_description(soup_of(scraper, '<html></html>')) is None


# --- extract_next_data ---------------------------------------------------

def test_extract_next_data(scraper):
    html = '<script id="__NEXT_DATA__">{"props": {"pageProps": {"x": 1}}}</script>'
    assert scraper.extract_next_data(soup_of(scraper, html))['props']['pageProps']['x'] == 1


def test_extract_next_data_invalid_json(scraper):
    html = '<script id="__NEXT_DATA__">{ rikki </script>'
    assert scraper.extract_next_data(soup_of(scraper, html)) is None


def test_extract_next_data_absent(scraper):
    assert scraper.extract_next_data(soup_of(scraper, '<html></html>')) is None


# --- extract_paragraphs --------------------------------------------------

ARTICLE_HTML = '''
<article>
    <p>Lyhyt.</p>
    <p>Tämä on riittävän pitkä kappale jotta se otetaan mukaan tulokseen.</p>
    <p>Lue myös: jokin muu juttu jota ei haluta mukaan ollenkaan tähän.</p>
    <p>Toinen riittävän pitkä kappale joka kuuluu varsinaiseen leipätekstiin.</p>
</article>
'''


def test_extract_paragraphs_filters_short_and_boilerplate(scraper):
    result = scraper.extract_paragraphs(soup_of(scraper, ARTICLE_HTML),
                                        min_length=30, skip_phrases=('lue myös',))
    assert 'Lyhyt' not in result
    assert 'Lue myös' not in result
    assert result.startswith('Tämä on riittävän pitkä')
    assert 'Toinen riittävän pitkä' in result


def test_extract_paragraphs_limit(scraper):
    result = scraper.extract_paragraphs(soup_of(scraper, ARTICLE_HTML),
                                        min_length=30, skip_phrases=('lue myös',), limit=1)
    assert 'Toinen riittävän pitkä' not in result


def test_extract_paragraphs_max_chars(scraper):
    result = scraper.extract_paragraphs(soup_of(scraper, ARTICLE_HTML),
                                        min_length=30, max_chars=20)
    assert len(result) == 20


def test_extract_paragraphs_skips_parent_classes(scraper):
    html = '''<article>
        <div class="promo"><p>Mainosteksti jota ei haluta mukaan tulokseen ollenkaan.</p></div>
        <p>Oikea leipätekstikappale joka kuuluu artikkeliin mukaan.</p>
    </article>'''
    result = scraper.extract_paragraphs(soup_of(scraper, html), min_length=30,
                                        skip_parent_classes=('promo',))
    assert 'Mainosteksti' not in result
    assert 'Oikea leipätekstikappale' in result


def test_extract_paragraphs_none_when_no_container(scraper):
    assert scraper.extract_paragraphs(soup_of(scraper, '<div><p>x</p></div>')) is None


def test_extract_paragraphs_none_when_nothing_qualifies(scraper):
    assert scraper.extract_paragraphs(soup_of(scraper, '<article><p>Lyhyt.</p></article>')) is None
