"""An editorial headline alone is not a film identity."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pytest
from scrapers.ts import TSScraper
from scrapers.il import ILScraper
from scrapers.ksml import KSMLScraper
from scrapers.sk import SKScraper
from scrapers.muropaketti import MuropakettiScraper
from scrapers.kulttuuritoimitus import KulttuuritoimitusScraper
from scrapers.demokraatti import DemokraattiScraper

HEADLINE='Arvio: Näyttelijän uskomaton paluu yllättää katsojan'

@pytest.mark.parametrize('cls',[TSScraper,ILScraper,KSMLScraper,SKScraper,MuropakettiScraper,KulttuuritoimitusScraper])
def test_headline_only_page_is_not_a_film(cls):
    body=f'<h1>IL-arvio: {HEADLINE}</h1><meta property="og:title" content="{HEADLINE}"><meta name="description" content="{HEADLINE}"><meta name="author" content="A Critic"><p>★★★★</p>'
    assert cls().parse_html(body) is None


def test_demokraatti_headline_without_film_infobox_is_not_a_title():
    assert DemokraattiScraper()._extract_title({'title':HEADLINE,'content':'<p>★★★★</p>'}) is None


def test_kulttuuritoimitus_api_keywords_and_headline_are_not_film_identity():
    item={'title':{'rendered':HEADLINE},'content':{'rendered':'<p>★★★★</p>'},
          '_embedded':{'author':[{'name':'A Critic'}]},'yoast_head_json':{'keywords':['Elokuvat']}}
    assert KulttuuritoimitusScraper().parse_json_api(item) is None


def test_il_facts_override_editorial_headline():
    document='<h1>IL-arvio: This is a long editorial headline</h1><div class="article-body"><h3>A Film</h3><h3>Suomi, 2026</h3><h3>IL-arvio: ★★★</h3></div><div class="author">A Critic</div>'
    review=ILScraper().parse_html(document)
    assert (review.movie_title,review.critic_name,review.rating_stars)==('A Film','A Critic',3)


@pytest.mark.parametrize('cls,body',[
    (TSScraper,'<p class="intro">A Film.</p>'),
    (KSMLScraper,'<p class="diks-storyline__lead-paragraph">A Film</p>'),
    (SKScraper,'<p>A Director: A Film. Elokuvateattereissa.</p>'),
    (MuropakettiScraper,'<p><strong>A Film</strong> Ensi-ilta: 20.11.2026</p>'),
    (KulttuuritoimitusScraper,'<div class="et_pb_text_inner"><p><b>A Film</b></p><ul><li>Ohjaus: A Director</li></ul></div>')])
def test_film_facts_survive_headline_rejection(cls,body):
    document=f'<h1>Arvio: {HEADLINE}</h1>{body}<meta name="author" content="A Critic"><p>★★★★</p>'
    review=cls().parse_html(document)
    assert review.movie_title=='A Film'
