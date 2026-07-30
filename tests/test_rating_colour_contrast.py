"""Arvosanavärien kontrastitestit.

Tähdet ovat aina valkoisia. Kaksi tummaa porrasta kantavat sen omin voimin ja
niiltä vaaditaan WCAG AA (4,5:1). Kolme vaaleinta ei voi täyttää sitä ilman
että kirkas kulta uhrataan, joten niillä luettavuus lepää tumman ääriviivan
varassa — ja testit vaativat että ääriviiva erottuu yhtä selvästi kuin musteen
muuten pitäisi.

Sävyt luetaan suoraan CSS-muuttujista, joten uusi värivalinta ei voi jäädä
lukukelvottomaksi huomaamatta. Aiempi asteikko epäonnistui pahasti: 3★
keltainen oli 1,66:1 eikä ääriviivaa ollut.
"""

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

CSS_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'css')

# Kaikki tähdet ovat valkoisia; portaat eroavat siinä, tarvitsevatko ne
# ääriviivan erottuakseen taustastaan.
SELF_SUFFICIENT_STEPS = (1, 2)   # tumma pohja kantaa valkoisen tähden sellaisenaan
OUTLINED_STEPS = (3, 4, 5)       # vaalea pohja: reunan tekee ääriviiva

WCAG_AA_SMALL_TEXT = 4.5
MARK_CONTRAST_MIN = 3.0     # merkin erottuminen taustasta


def _read(name):
    with open(os.path.join(CSS_DIR, name), encoding='utf-8') as f:
        return f.read()


def _tokens():
    """Poimi :root-muuttujat base.css:stä."""
    css = _read('base.css')
    return dict(re.findall(r'(--[\w-]+):\s*(#[0-9a-fA-F]{3,8})\s*;', css))


def _srgb_to_linear(channel):
    c = channel / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_colour):
    h = hex_colour.lstrip('#')
    if len(h) == 3:
        h = ''.join(ch * 2 for ch in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (0.2126 * _srgb_to_linear(r)
            + 0.7152 * _srgb_to_linear(g)
            + 0.0722 * _srgb_to_linear(b))


def contrast(a, b):
    la, lb = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@pytest.fixture(scope='module')
def tokens():
    return _tokens()


def test_contrast_helper_matches_known_values():
    """Varmista laskenta tunnetuilla ääripäillä."""
    assert contrast('#000000', '#ffffff') == pytest.approx(21.0, abs=0.01)
    assert contrast('#ffffff', '#ffffff') == pytest.approx(1.0, abs=0.01)


def test_all_five_steps_are_defined(tokens):
    for step in range(1, 6):
        assert f'--star-{step}' in tokens, f'--star-{step} puuttuu base.css:stä'
    assert '--star-ink' in tokens
    assert '--star-outline' in tokens


def _gradient_stops(tokens, step):
    """Portaan kaikki kolme pysäkkiä ylhäältä alas."""
    return (tokens[f'--star-{step}-top'],
            tokens[f'--star-{step}'],
            tokens[f'--star-{step}-bot'])


@pytest.mark.parametrize('step', SELF_SUFFICIENT_STEPS)
def test_dark_steps_readable_at_every_gradient_stop(tokens, step):
    """Kahdella tummalla portaalla valkoinen tähti kantaa ilman ääriviivaa.

    Pilli on gradientti, joten kontrastin on kestettävä sen jokaisessa kohdassa.
    Tämä ei ole teoreettista: 2★:n ylin pysäkki putosi 4,22:1:een kun sitä
    vaalennettiin muiden portaiden tapaan 6 %, ja nosto jouduttiin puolittamaan.
    """
    for stop in _gradient_stops(tokens, step):
        ratio = contrast(tokens['--star-ink'], stop)
        assert ratio >= WCAG_AA_SMALL_TEXT, (
            f'{step}★ pysäkki {stop} valkoisella tähdellä vain {ratio:.2f}:1')


@pytest.mark.parametrize('step', OUTLINED_STEPS)
def test_light_steps_outline_separates_from_every_gradient_stop(tokens, step):
    """Vaaleilla portailla luettavuus lepää ääriviivan varassa.

    Valkoinen tähti kirkkaalla kullalla on 1,41:1 eli WCAG:n mittarilla
    lukukelvoton; reunan tekee ääriviiva. Siksi ääriviivan on erotuttava
    portaan sävystä yhtä selvästi kuin musteen muuten pitäisi.
    """
    for stop in _gradient_stops(tokens, step):
        ratio = contrast(tokens['--star-outline'], stop)
        assert ratio >= WCAG_AA_SMALL_TEXT, (
            f'{step}★ pysäkki {stop} vs ääriviiva vain {ratio:.2f}:1')


@pytest.mark.parametrize('step', OUTLINED_STEPS)
def test_light_steps_declare_an_outline(step):
    """Ilman ääriviivaa vaaleiden portaiden tähdet katoaisivat kokonaan."""
    table = _read('table.css')
    block = re.search(
        r'\.stars-3 \.rating-stars,\s*\.stars-4 \.rating-stars,\s*'
        r'\.stars-5 \.rating-stars\s*\{([^}]*)\}', table, re.S)
    assert block, 'vaaleiden portaiden ääriviivasääntöä ei löytynyt'
    assert 'text-shadow' in block.group(1)
    assert 'var(--star-outline)' in block.group(1)


def test_all_stars_use_the_same_ink(tokens):
    """Muste ei saa vaihtua kesken asteikon — se oli C-variantin koko pointti."""
    table = _read('table.css')
    assert '--pill-ink' not in table, 'porraskohtainen muste on yhä käytössä'
    assert tokens['--star-ink'] == '#ffffff'


@pytest.mark.parametrize('step', range(1, 6))
def test_gradient_darkens_downward(tokens, step):
    """Alareunan on oltava tummin: siitä syntyy pillin raja ilman reunusviivaa."""
    top, mid, bot = _gradient_stops(tokens, step)
    assert relative_luminance(top) > relative_luminance(mid) > relative_luminance(bot), (
        f'{step}★ gradientti ei syvene alaspäin: {top} → {mid} → {bot}')


def test_pills_have_no_border_rule():
    """Raja tulee gradientista, ei reunusviivasta."""
    table = _read('table.css')
    block = re.search(r'\.rating-pill\s*\{([^}]*)\}', table)
    assert block, '.rating-pill-sääntöä ei löytynyt'
    assert 'border:' not in block.group(1), 'pillillä on yhä reunus'


def test_sparkline_is_monochrome(tokens):
    """Väriasteikko on pilleissä; sparklinessa arvosanan kertoo palkin paikka."""
    table = _read('table.css')
    for step in range(1, 6):
        assert f'--star-{step})' not in _sparkline_block(table), (
            'sparkline käyttää pillien väriasteikkoa')
    assert '--spark-bar-top' in tokens and '--spark-bar-bot' in tokens


def _sparkline_block(table_css):
    start = table_css.find('.spark-bar {')
    assert start != -1, '.spark-bar-sääntöä ei löytynyt'
    return table_css[start:start + 400]


def test_sparkline_bar_stands_out_from_track(tokens):
    """Palkin on erotuttava sekä lokerostaan että sivun taustasta."""
    track = tokens['--spark-track']
    for name in ('--spark-bar-top', '--spark-bar-bot'):
        assert contrast(tokens[name], track) >= MARK_CONTRAST_MIN, (
            f'{name} {tokens[name]} vain {contrast(tokens[name], track):.2f}:1 lokeroa vasten')
        assert contrast(tokens[name], '#ffffff') >= MARK_CONTRAST_MIN, (
            f'{name} {tokens[name]} liian haalea valkoista vasten')


# Pinnat joilla sparkline esiintyy: taulukon solu, seepraraidat ja
# mobiilikortin harmaa otsikko. Viimeinen on tiukin.
SPARKLINE_SURFACES = {
    'taulukon solu': '#ffffff',
    'seepra pariton': '#fcfcfc',
    'seepra parillinen': '#f8faff',
    'seepra risteys': '#f0f4ff',
    'mobiilikortin otsikko': '#f8f9fa',
}


@pytest.mark.parametrize('name,surface', sorted(SPARKLINE_SURFACES.items()))
def test_sparkline_track_visible_on_every_surface(tokens, name, surface):
    """Lokeron pitää erottua kaikilla pinnoilla joilla sparkline esiintyy.

    Mobiilikortin otsikko on harmaa, joten valkoista vasten sopiva lokero voi
    kadota siellä kokonaan — juuri siinä näkymässä jossa sparkline on
    näkyvimmillään.
    """
    ratio = contrast(tokens['--spark-track'], surface)
    assert ratio >= 1.3, f'lokero katoaa pinnalla {name} ({surface}): {ratio:.2f}:1'


def test_sparkline_track_stays_recessive(tokens):
    """Lokero ei saa olla niin tumma että se kilpailee palkin kanssa."""
    ratio = contrast(tokens['--spark-track'], '#ffffff')
    assert ratio <= 1.8, f'lokero {tokens["--spark-track"]} on liian vahva: {ratio:.2f}:1'


def test_pill_ink_survives_link_hover():
    """Pilli on <a>, joten base.css:n yleinen a:hover värjäisi tähdet violetiksi.

    Regressio: kun .rating-stars vaihdettiin arvoon 'color: inherit', se menetti
    suojan a:hoveria vastaan ja tähdet vaihtoivat väriä hiiren alla.
    """
    table = _read('table.css')
    assert re.search(r'\.rating-pill:hover[^{]*\{[^}]*color:', table, re.S), (
        '.rating-pill:hover ei aseta väriä — a:hover voittaa ja tähdet vaihtavat väriä')


def test_pill_hover_does_not_change_colour():
    """Hover saa suurentaa ja varjostaa, muttei muuttaa pillin väriä."""
    table = _read('table.css')
    block = re.search(r'\.rating-pill:hover\s*\{([^}]*)\}', table)
    assert block, '.rating-pill:hover -sääntöä ei löytynyt'
    body = block.group(1)
    for forbidden in ('background', 'filter', 'opacity'):
        assert forbidden not in body, f'hover muuttaa ulkoasua: {forbidden}'
