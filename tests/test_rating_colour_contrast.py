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


@pytest.mark.parametrize('step', LIGHT_INK_STEPS)
def test_dark_steps_readable_with_light_ink(tokens, step):
    ratio = contrast(tokens['--star-ink-light'], tokens[f'--star-{step}'])
    assert ratio >= WCAG_AA_SMALL_TEXT, (
        f'{step}★ {tokens[f"--star-{step}"]} vaalealla musteella vain {ratio:.2f}:1')


@pytest.mark.parametrize('step', DARK_INK_STEPS)
def test_light_steps_readable_with_dark_ink(tokens, step):
    ratio = contrast(tokens['--star-ink-dark'], tokens[f'--star-{step}'])
    assert ratio >= WCAG_AA_SMALL_TEXT, (
        f'{step}★ {tokens[f"--star-{step}"]} tummalla musteella vain {ratio:.2f}:1')


def test_light_steps_have_an_edge_in_css():
    """Vaaleat portaat eivät erotu valkoisesta sivusta, joten ne tarvitsevat reunuksen."""
    table = _read('table.css')
    block = re.search(r'\.stars-3,\s*\.stars-4,\s*\.stars-5\s*\{([^}]*)\}', table)
    assert block, 'vaaleiden portaiden yhteissääntöä ei löytynyt table.css:stä'
    body = block.group(1)
    assert 'border-color' in body, 'vaaleilta pilleiltä puuttuu reunus'
    assert 'var(--star-ink-dark)' in body, 'vaaleilta pilleiltä puuttuu tumma muste'


@pytest.mark.parametrize('step', range(1, 6))
def test_sparkline_tones_visible_against_page(tokens, step):
    """Sparklinen palkit ovat pieniä merkkejä: niiden on erotuttava sivun taustasta."""
    tone = tokens[f'--spark-{step}']
    ratio = contrast(tone, '#ffffff')
    assert ratio >= MARK_CONTRAST_MIN, (
        f'sparkline {step}★ {tone} vain {ratio:.2f}:1 valkoista vasten')


def test_sparkline_tones_are_separate_from_pill_tones(tokens):
    """Sparkline ei saa periä kirkasta kultaa: se katoaisi vaaleaa taustaa vasten."""
    assert tokens['--spark-5'] != tokens['--star-5'], (
        'sparkline käyttää pillin sävyä — kirkas kulta on 1,4:1 valkoista vasten')
