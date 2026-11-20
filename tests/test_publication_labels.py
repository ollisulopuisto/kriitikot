"""Full publication names without changing visible codes or filtering IDs."""
import sys
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'src'))
from app import app
from publication_names import publication_name, publication_names


def test_publication_names_preserve_unknown_and_expand_aliases():
    assert publication_name('IS') == 'Ilta-Sanomat'
    assert publication_name('ts') == 'Turun Sanomat'
    assert publication_names(['MURO','KUTO','SK']) == 'Muropaketti, Kulttuuritoimitus, Suomen Kuvalehti'
    assert publication_name('UNKNOWN') == 'UNKNOWN'


def test_filter_chips_and_critic_tags_have_full_names():
    response=app.test_client().get('/')
    assert response.status_code == 200
    soup=BeautifulSoup(response.data,'html.parser')
    chips=soup.select('.media-filter-btn')
    assert chips
    for chip in chips:
        code=chip['data-publication']
        assert chip['title'] == publication_name(code)
        assert chip['aria-label'] == publication_name(code)
        assert chip.get_text(strip=True) == code
    for label in soup.select('.critic-media'):
        codes=label.get_text(strip=True).split(', ')
        assert label['title'] == publication_names(codes)
        assert label['aria-label'] == publication_names(codes)
    for label in soup.select('.review-media'):
        assert label['title'] == publication_name(label.get_text(strip=True))
