"""Arvosanavärien kontrastitestit.

Arvosanapilleissä on teksti värillisen taustan päällä, joten jokaisen portaan on
täytettävä WCAG AA (4.5:1 pienelle tekstille). Tämä testi lukee sävyt suoraan
CSS-muuttujista, joten uusi värivalinta ei voi vahingossa jäädä lukukelvottomaksi.

Aiempi asteikko epäonnistui tässä pahasti: 3★ keltainen oli 1,66:1 valkoisella
tekstillä eli tähdet olivat käytännössä näkymättömät.
"""

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

CSS_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'css')

# Musteparit vastaavat table.css:n .stars-N -sääntöjä
LIGHT_INK_STEPS = (1, 2)   # valkoinen muste tummalla taustalla
DARK_INK_STEPS = (3, 4, 5)  # tumma muste vaalealla taustalla

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
    assert '--star-ink-dark' in tokens
    assert '--star-ink-light' in tokens


def _gradient_stops(tokens, step):
    """Portaan kaikki kolme pysäkkiä ylhäältä alas."""
    return (tokens[f'--star-{step}-top'],
            tokens[f'--star-{step}'],
            tokens[f'--star-{step}-bot'])


@pytest.mark.parametrize('step', LIGHT_INK_STEPS)
def test_dark_steps_readable_at_every_gradient_stop(tokens, step):
    """Pilli on gradientti, joten kontrastin on kestettävä sen jokaisessa kohdassa.

    Tämä ei ole teoreettista: 2★:n ylin pysäkki putosi 4,22:1:een kun sitä
    vaalennettiin muiden portaiden tapaan 6 %, ja nosto jouduttiin puolittamaan.
    """
    for stop in _gradient_stops(tokens, step):
        ratio = contrast(tokens['--star-ink-light'], stop)
        assert ratio >= WCAG_AA_SMALL_TEXT, (
            f'{step}★ pysäkki {stop} vaalealla musteella vain {ratio:.2f}:1')


@pytest.mark.parametrize('step', DARK_INK_STEPS)
def test_light_steps_readable_at_every_gradient_stop(tokens, step):
    for stop in _gradient_stops(tokens, step):
        ratio = contrast(tokens['--star-ink-dark'], stop)
        assert ratio >= WCAG_AA_SMALL_TEXT, (
            f'{step}★ pysäkki {stop} tummalla musteella vain {ratio:.2f}:1')


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


def test_sparkline_track_is_visible_but_recessive(tokens):
    """Lokeron pitää näkyä valkoisella mutta ei kilpailla palkin kanssa."""
    ratio = contrast(tokens['--spark-track'], '#ffffff')
    assert 1.1 <= ratio <= 1.8, f'lokero {tokens["--spark-track"]} on {ratio:.2f}:1 valkoista vasten'


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
