from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from bs4 import BeautifulSoup
from scrapers.episodi import EpisodiScraper

FIXTURES = Path(__file__).with_name('fixtures') / 'episodi'


def test_real_you_can_see_everything_page_keeps_accented_signature():
    page = (FIXTURES / 'you-can-see-everything.html').read_text()
    review = EpisodiScraper().parse_html(page)
    assert review.critic_name == 'Werneri Pihlajamäki'


def test_real_cliff_booth_page_uses_review_author_not_footer_editor():
    page = (FIXTURES / 'cliff-booth.html').read_text()
    review = EpisodiScraper().parse_html(page)
    assert review.critic_name == 'Daniel Bradshaw'
    assert review.rating_stars == 4


def test_unrelated_italic_name_does_not_override_review_author():
    page = (FIXTURES / 'you-can-see-everything.html').read_text()
    page = page.replace('Werneri Pihlajamäki</em>', 'David Fincher</em>')
    assert EpisodiScraper().parse_html(page).critic_name == 'Werneri Pihlajamaki'


def test_footer_author_is_not_the_critic():
    soup = BeautifulSoup('<footer><a href="/author/jussihuhtala/">Jussi Huhtala</a></footer>', 'html.parser')
    assert EpisodiScraper()._extract_critic(soup) == 'Episodi'


def test_legacy_byline_still_works():
    soup = BeautifulSoup('<a href="/kirjoittajat/test/">Test Critic</a>', 'html.parser')
    assert EpisodiScraper()._extract_critic(soup) == 'Test Critic'
