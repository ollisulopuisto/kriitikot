#!/usr/bin/env python3
"""
Esimerkki: Miten käyttää scraper-kirjastoa
"""

from scraper import HSScraper, KSMLScraper, ILScraper, TSScraper, scrape_review
import os


def example_1_basic_usage():
    """Perusesimerkki: Parsi yksi HS-arvostelu."""
    print("=" * 60)
    print("ESIMERKKI 1: Perus HS-scraper")
    print("=" * 60)
    
    scraper = HSScraper()
    test_file = os.path.join(
        os.path.dirname(__file__),
        '../tests/test_data/hs_review_1.html'
    )
    
    review = scraper.parse_file(test_file)
    
    if review:
        print(f"\n📽️  Elokuva: {review.movie_title}")
        print(f"✍️  Kriitikko: {review.critic_name}")
        print(f"⭐ Arvosana: {'★' * review.rating_stars}{'☆' * (5 - review.rating_stars)} ({review.rating_stars}/5)")
        print(f"📰 Julkaisu: {review.source_publication}")
        print(f"🔗 URL: {review.source_url}")
        print(f"\n💬 Arvostelu:")
        print(f"   {review.review_text}")
    else:
        print("❌ Arvostelun parsiminen epäonnistui")
    
    print()


def example_2_multiple_sources():
    """Esimerkki: Käytä yleistä scrape_review-funktiota."""
    print("=" * 60)
    print("ESIMERKKI 2: Yleinen scrape_review()-funktio")
    print("=" * 60)
    
    test_file = os.path.join(
        os.path.dirname(__file__),
        '../tests/test_data/hs_review_1.html'
    )
    
    with open(test_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Käytä yleistä funktiota joka valitsee oikean scraperin
    review = scrape_review(
        html_content,
        source='hs',  # Voit vaihtaa lähdettä: 'ksml', 'il', 'yle', etc.
        source_url='https://www.hs.fi/taide/art-2000011556702.html'
    )
    
    if review:
        print(f"\n✅ Parsittiin arvostelu lähteestä: {review.source_publication}")
        print(f"   Elokuva: {review.movie_title}")
        print(f"   Arvosana: {review.rating_stars}/5 ⭐")
    
    print()


def example_2b_ksml_source():
    """Esimerkki: KSML.fi arvostelun parsinta."""
    print("=" * 60)
    print("ESIMERKKI 2B: KSML (Keskisuomalainen) scraper")
    print("=" * 60)
    
    test_file = os.path.join(
        os.path.dirname(__file__),
        '../tests/test_data/ksml_review_1.html'
    )
    
    # Suora scraper-käyttö
    scraper = KSMLScraper()
    review = scraper.parse_file(test_file)
    
    if review:
        print(f"\n📽️  Elokuva: {review.movie_title}")
        print(f"✍️  Kriitikko: {review.critic_name}")
        if review.rating_stars:
            print(f"⭐ Arvosana: {'★' * review.rating_stars}{'☆' * (5 - review.rating_stars)} ({review.rating_stars}/5)")
        else:
            print(f"⭐ Arvosana: Ei mainittu")
        print(f"📰 Julkaisu: {review.source_publication}")
        
        if review.review_text:
            preview = review.review_text[:150] + '...' if len(review.review_text) > 150 else review.review_text
            print(f"\n💬 Arvostelu (alku):")
            print(f"   {preview}")
    else:
        print("❌ Arvostelun parsiminen epäonnistui")
    
    # Vaihtoehtoisesti yleisen funktion kautta:
    print("\n🔄 Sama yleisellä scrape_review()-funktiolla:")
    with open(test_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    review2 = scrape_review(html, source='ksml', source_url='https://www.ksml.fi/paikalliset/8924414')
    if review2:
        print(f"   ✅ {review2.movie_title} - {review2.rating_stars}/5★")
    
    print()


def example_2c_il_source():
    """Esimerkki: Iltalehden arvostelun parsinta."""
    print("=" * 60)
    print("ESIMERKKI 2C: IL (Iltalehti) scraper")
    print("=" * 60)
    
    test_file = os.path.join(
        os.path.dirname(__file__),
        '../tests/test_data/il_review_1.html'
    )
    
    # Suora scraper-käyttö
    scraper = ILScraper()
    review = scraper.parse_file(test_file)
    
    if review:
        print(f"\n📽️  Elokuva: {review.movie_title}")
        print(f"✍️  Kriitikko: {review.critic_name}")
        if review.rating_stars:
            print(f"⭐ Arvosana: {'★' * review.rating_stars}{'☆' * (5 - review.rating_stars)} ({review.rating_stars}/5)")
        else:
            print(f"⭐ Arvosana: Ei mainittu")
        print(f"📰 Julkaisu: {review.source_publication}")
        
        if review.review_text:
            preview = review.review_text[:150] + '...' if len(review.review_text) > 150 else review.review_text
            print(f"\n💬 Arvostelu (alku):")
            print(f"   {preview}")
    else:
        print("❌ Arvostelun parsiminen epäonnistui")
    
    # Vaihtoehtoisesti yleisen funktion kautta:
    print("\n🔄 Sama yleisellä scrape_review()-funktiolla:")
    with open(test_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    review2 = scrape_review(html, source='il', source_url='https://www.iltalehti.fi/tv-ja-leffat/a/847c8833')
    if review2:
        print(f"   ✅ {review2.movie_title} - {review2.rating_stars}/5★")
    
    print()


def example_2d_ts_source():
    """Esimerkki: Turun Sanomien arvostelun parsinta."""
    print("=" * 60)
    print("ESIMERKKI 2D: TS (Turun Sanomat) scraper")
    print("=" * 60)
    
    test_file = os.path.join(
        os.path.dirname(__file__),
        '../tests/test_data/ts_review_1.html'
    )
    
    # Suora scraper-käyttö
    scraper = TSScraper()
    review = scraper.parse_file(test_file)
    
    if review:
        print(f"\n📽️  Elokuva: {review.movie_title}")
        print(f"✍️  Kriitikko: {review.critic_name}")
        if review.rating_stars:
            print(f"⭐ Arvosana: {'★' * review.rating_stars}{'☆' * (5 - review.rating_stars)} ({review.rating_stars}/5)")
        else:
            print(f"⭐ Arvosana: Ei mainittu")
        print(f"📰 Julkaisu: {review.source_publication}")
        
        if review.review_text:
            preview = review.review_text[:150] + '...' if len(review.review_text) > 150 else review.review_text
            print(f"\n💬 Arvostelu (alku):")
            print(f"   {preview}")
    else:
        print("❌ Arvostelun parsiminen epäonnistui")
    
    # Vaihtoehtoisesti yleisen funktion kautta:
    print("\n🔄 Sama yleisellä scrape_review()-funktiolla:")
    with open(test_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    review2 = scrape_review(html, source='ts', source_url='https://www.ts.fi/kulttuuri/6796149')
    if review2:
        print(f"   ✅ {review2.movie_title} - {review2.rating_stars}/5★")
    
    print()


def example_3_to_dict():
    """Esimerkki: Muunna Review sanakirjaksi (esim. JSON:ia varten)."""
    print("=" * 60)
    print("ESIMERKKI 3: Review -> Dictionary (JSON-yhteensopiva)")
    print("=" * 60)
    
    scraper = HSScraper()
    test_file = os.path.join(
        os.path.dirname(__file__),
        '../tests/test_data/hs_review_1.html'
    )
    
    review = scraper.parse_file(test_file)
    
    if review:
        data = review.to_dict()
        
        print("\n📋 Review sanakirjana:")
        import json
        print(json.dumps(data, indent=2, ensure_ascii=False))
    
    print()


def example_4_filter_reviews():
    """Esimerkki: Suodata arvostelut arvosanan perusteella."""
    print("=" * 60)
    print("ESIMERKKI 4: Suodata arvostelut")
    print("=" * 60)
    
    # Tässä esimerkissä olisi lista arvosteluja
    # Nyt käytetään vain yhtä demo-arvostelua
    scraper = HSScraper()
    test_file = os.path.join(
        os.path.dirname(__file__),
        '../tests/test_data/hs_review_1.html'
    )
    
    reviews = [scraper.parse_file(test_file)]  # Oikeasti olisi monta
    
    # Suodata vain huonot arvostelut (1-2 tähteä)
    bad_reviews = [r for r in reviews if r and r.rating_stars and r.rating_stars <= 2]
    
    # Suodata vain hyvät arvostelut (4-5 tähteä)
    good_reviews = [r for r in reviews if r and r.rating_stars and r.rating_stars >= 4]
    
    print(f"\n📊 Tilastot:")
    print(f"   Huonoja arvosteluja (≤2★): {len(bad_reviews)}")
    print(f"   Hyviä arvosteluja (≥4★): {len(good_reviews)}")
    
    if bad_reviews:
        print(f"\n⚠️  Huonot arvostelut:")
        for r in bad_reviews:
            print(f"   - {r.movie_title}: {r.rating_stars}★")
    
    print()


def example_5_adding_new_source():
    """Esimerkki: Template uuden lähteen lisäämiseen."""
    print("=" * 60)
    print("ESIMERKKI 5: Template uudelle scraperille")
    print("=" * 60)
    
    print("""
# Näin lisäisit uuden lähteen (esim. Ilta-Sanomat):

from scraper import Review
from typing import Optional
from bs4 import BeautifulSoup

class ILScraper:
    '''Ilta-Sanomien arvostelujen parsija.'''
    
    def __init__(self):
        self.publication_name = "Ilta-Sanomat"
    
    def parse_html(self, html_content: str, source_url: Optional[str] = None) -> Optional[Review]:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # TODO: Toteuta IL:n HTML-rakenteen parsinta
        # 1. Etsi elokuvan nimi
        # 2. Etsi kriitikon nimi
        # 3. Etsi tähtiarvio
        # 4. Etsi arvosteluteksti
        
        return Review(
            movie_title="...",
            critic_name="...",
            rating_stars=...,
            review_text="...",
            source_url=source_url,
            source_publication=self.publication_name
        )

# Lisää scraper scrape_review()-funktioon:
# scrapers = {
#     'hs': HSScraper(),
#     'il': ILScraper(),  # <-- Tähän!
# }
""")
    print()


if __name__ == '__main__':
    print("\n🎬 ELOKUVAKRITIIKKIEN KERÄÄJÄ - ESIMERKKEJÄ\n")
    
    example_1_basic_usage()
    example_2_multiple_sources()
    example_2b_ksml_source()
    example_2c_il_source()
    example_2d_ts_source()
    example_3_to_dict()
    example_4_filter_reviews()
    example_5_adding_new_source()
    
    print("=" * 60)
    print("✅ Kaikki esimerkit suoritettu!")
    print("=" * 60)
    print("\n💡 Seuraavat askeleet:")
    print("   1. Tutustu README.md:hen")
    print("   2. Aja testit: pytest tests/test_scraper.py -v")
    print("   3. Käynnistä web-sovellus: python src/app.py")
    print()
