"""Contrast checks for colored A1v3c stars and monochrome sparklines."""

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

CSS_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'css')

WCAG_AA_SMALL_TEXT = 4.5
MARK_CONTRAST_MIN = 3.0     # merkin erottuminen taustasta


def _read(name):
    with open(os.path.join(CSS_DIR, name), encoding='utf-8') as f:
        return f.read()


def _tokens():
    """Poimi :root-muuttujat base.css:stä."""
    css = _read('base.css')
    return dict(re.findall(r'(--[\w-]+):\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\))\s*;', css))


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


def _parse_rgba(value):
    """rgba(r, g, b, a) -> (r, g, b, a). Palauttaa None jos ei rgba."""
    m = re.match(r'rgba?\(([^)]*)\)', value)
    if not m:
        return None
    parts = [p.strip() for p in m.group(1).split(',')]
    r, g, b = (int(x) for x in parts[:3])
    a = float(parts[3]) if len(parts) > 3 else 1.0
    return r, g, b, a


def composite(value, surface):
    """Sekoita mahdollisesti läpikuultava sävy taustapinnan päälle."""
    rgba = _parse_rgba(value)
    if rgba is None:
        return value
    r, g, b, a = rgba
    sh = surface.lstrip('#')
    sr, sg, sb = (int(sh[i:i + 2], 16) for i in (0, 2, 4))
    return '#%02x%02x%02x' % tuple(
        round(a * c + (1 - a) * s) for c, s in ((r, sr), (g, sg), (b, sb)))


@pytest.fixture(scope='module')
def tokens():
    return _tokens()


def test_contrast_helper_matches_known_values():
    """Varmista laskenta tunnetuilla ääripäillä."""
    assert contrast('#000000', '#ffffff') == pytest.approx(21.0, abs=0.01)
    assert contrast('#ffffff', '#ffffff') == pytest.approx(1.0, abs=0.01)


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


def test_sparkline_bar_visible_against_page(tokens):
    """Palkin on erotuttava myös sivun taustasta, ei vain lokerosta."""
    for name in ('--spark-bar-top', '--spark-bar-bot'):
        assert contrast(tokens[name], '#ffffff') >= MARK_CONTRAST_MIN, (
            f'{name} {tokens[name]} liian haalea valkoista vasten')


# Pinnat joilla sparkline esiintyy. Rivin osumaväri on tiukin: siinä sekä
# lokero että palkki joutuvat erottumaan violetilta gradientilta.
SPARKLINE_SURFACES = {
    'taulukon solu': '#ffffff',
    'seepra pariton': '#fcfcfc',
    'seepra parillinen': '#f8faff',
    'seepra risteys': '#f0f4ff',
    'mobiilikortin otsikko': '#f8f9fa',
    'rivin osumaväri vaalea': '#e8d5ff',
    'rivin osumaväri tumma': '#d4bbff',
}


@pytest.mark.parametrize('name,surface', sorted(SPARKLINE_SURFACES.items()))
def test_sparkline_track_visible_on_every_surface(tokens, name, surface):
    """Lokeron on erotuttava kaikilla pinnoilla joilla sparkline esiintyy.

    Kiinteä sävy katosi aina jollakin pinnalla: #e7e5e4 oli mobiilikortin
    otsikkoa vasten 1,19:1 ja #d4cfca rivin osumaväriä vasten 1,10:1.
    Läpikuultava lokero tummentaa mitä tahansa alla olevaa pintaa.
    """
    track = composite(tokens['--spark-track'], surface)
    ratio = contrast(track, surface)
    assert ratio >= 1.3, f'lokero katoaa pinnalla {name} ({surface}): {ratio:.2f}:1'


@pytest.mark.parametrize('name,surface', sorted(SPARKLINE_SURFACES.items()))
def test_sparkline_bar_stands_out_from_track_everywhere(tokens, name, surface):
    """Palkin on erotuttava lokerostaan myös rivin osumavärillä."""
    track = composite(tokens['--spark-track'], surface)
    ratio = contrast(tokens['--spark-bar-top'], track)
    assert ratio >= MARK_CONTRAST_MIN, (
        f'palkki sulautuu lokeroon pinnalla {name}: {ratio:.2f}:1')


def test_sparkline_track_stays_recessive(tokens):
    """Lokero ei saa olla niin tumma että se kilpailee palkin kanssa."""
    track = composite(tokens['--spark-track'], '#ffffff')
    assert contrast(track, '#ffffff') <= 1.8, f'lokero liian vahva: {track}'


def test_cluster_ink_separates_from_light_surfaces():
    """A1v3c uses colored shapes, not white glyphs on colored pills."""
    table = _read('table.css')
    blocks = re.findall(r'\.rating-pill\.stars-[1-5]\s*\{([^}]+)\}', table)
    assert len(blocks) == 5
    for block in blocks:
        color = re.search(r'--cluster-color: (#[0-9a-f]+)', block).group(1)
        edge = re.search(r'--cluster-edge: (#[0-9a-f]+)', block)
        if edge:
            color = edge.group(1)
        for surface in ('#ffffff', '#f0f4ff', '#fcfcfc', '#f8f9fa', '#ede9fe'):
            assert contrast(color, surface) >= 3
    assert '--cluster-wash' not in table


def test_five_star_cluster_glows_without_a_face_shadow():
    table = _read('table.css')
    block = re.search(
        r'\.rating-pill\.stars-5 \.rating-star-paint\s*\{([^}]*)\}', table, re.S)
    assert block and 'drop-shadow' in block.group(1)
    assert '#bbf7d0' in block.group(1)
    assert 'box-shadow' not in block.group(1)
