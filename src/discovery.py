"""
Discovery-moduuli: Löytää uudet elokuva-arvostelut automaattisesti.

Tämä moduuli sisältää "metascraperin" joka:
1. Crawlaa kategoriasivuja ja JSON-API:ta
2. Tunnistaa arvostelut
3. Palauttaa URL-listoja jatkokäsittelyä varten

Tuetut lähteet:
- TS: HTML category page (ts.fi/kulttuuri/)
- IL: JSON API (iltalehti.fi/tv-ja-leffat)
- KSML: HTML search page (ksml.fi/haku/)
"""

from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import requests
import re
import json
from datetime import datetime


class CategoryCrawler:
    """Crawlaa kategoriasivuja ja löytää linkejä arvosteluihin."""
    
    # Kategoriasivut joilta arvostelut löytyvät
    CATEGORY_PAGES = {
        'sk': 'https://suomenkuvalehti.fi/avainsana/elokuva/',
        'ts': 'https://www.ts.fi/kulttuuri/',
        'il': 'https://www.iltalehti.fi/tv-ja-leffat',
        'ksml': 'https://www.ksml.fi/haku/?q=Elokuva-arvio',
    }
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def find_review_links(self, source: str, limit: int = 20) -> List[Dict[str, str]]:
        """
        Palauttaa arvostelu-URL:t kategoriasivulta.
        
        Args:
            source: Lähteen tunniste ('sk', 'hs', 'ts', 'il', 'ksml')
            limit: Montako arvostelua max palautetaan
            
        Returns:
            Lista dictionaryja, joissa 'title' ja 'url'
        """
        url = self.CATEGORY_PAGES.get(source)
        if not url:
            raise ValueError(f"Unknown source: {source}")
        
        # Lähdekohtainen logiikka
        if source == 'sk':
            html = self._fetch_url(url)
            soup = BeautifulSoup(html, 'html.parser')
            return self._find_sk_reviews(soup, limit)
        
        elif source == 'ts':
            html = self._fetch_url(url)
            soup = BeautifulSoup(html, 'html.parser')
            return self._find_ts_reviews(soup, limit)
        
        elif source == 'il':
            html = self._fetch_url(url)
            soup = BeautifulSoup(html, 'html.parser')
            return self._find_il_reviews(soup, url)
        
        elif source == 'ksml':
            html = self._fetch_url(url)
            soup = BeautifulSoup(html, 'html.parser')
            return self._find_ksml_reviews(soup, limit)
        
        return []
    
    def _find_sk_reviews(self, soup: BeautifulSoup, limit: int) -> List[Dict[str, str]]:
        """Löytää Suomen Kuvalehden arvostelut."""
        reviews = []
        
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            
            # SK:n arvostelut alkavat "Arvio:"
            if text.startswith('Arvio:'):
                url = link['href']
                
                # Muodosta absoluuttinen URL
                if url.startswith('/'):
                    url = 'https://suomenkuvalehti.fi' + url
                
                reviews.append({
                    'title': text,
                    'url': url
                })
                
                if len(reviews) >= limit:
                    break
        
        return reviews
    
    def _find_ts_reviews(self, soup: BeautifulSoup, limit: int) -> List[Dict[str, str]]:
        """Löytää Turun Sanomien arvostelut kategoriasivulta."""
        reviews = []
        
        # TS käyttää <span>Elokuva-arvostelu</span> tageja
        for tag in soup.find_all('span', string='Elokuva-arvostelu'):
            # Etsi lähimmän <a> elementin
            article_div = tag.find_parent('div', class_='article')
            if article_div:
                # Hae article ID
                article_id = article_div.get('data-articleid')
                
                # Hae otsikko
                header = article_div.find('span', class_='header')
                if header and article_id:
                    title = header.get_text(strip=True)
                    url = f'https://www.ts.fi/kulttuuri/{article_id}'
                    
                    reviews.append({
                        'title': title,
                        'url': url
                    })
                    
                    if len(reviews) >= limit:
                        break
        
        return reviews
    
    def _find_il_reviews(self, soup, base_url):
        """Find IL movie reviews from embedded JSON data"""
        reviews = []
        
        # IL embeds article data in a script tag with __NUXT_DATA__
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and '"headline"' in script.string and 'IL-arvio' in script.string:
                try:
                    # Try to extract article data from JSON
                    # Look for patterns like: "headline":"IL-arvio: ..."
                    import re
                    
                    # Find all articles with IL-arvio in headline
                    article_pattern = r'"article_id":"([^"]+)".*?"headline":"(IL-arvio[^"]+)"'
                    matches = re.findall(article_pattern, script.string, re.DOTALL)
                    
                    for article_id, headline in matches:
                        # Construct URL from article ID
                        url = f"https://www.iltalehti.fi/tv-ja-leffat/a/{article_id}"
                        reviews.append({
                            'title': headline.strip(),
                            'url': url
                        })
                        
                        # Limit to a few reviews
                        if len(reviews) >= 5:
                            break
                except Exception as e:
                    print(f"  [IL] JSON parsing error: {e}")
                    continue
        
        return reviews
    
    def _find_ksml_reviews(self, soup: BeautifulSoup, limit: int) -> List[Dict[str, str]]:
        """Löytää Keskisuomalaisen arvostelut hakusivulta."""
        reviews = []
        
        # KSML käyttää hakua, etsitään artikkeleita
        for link in soup.find_all('a', href=True):
            # Tarkista onko linkki artikkelin otsikko
            href = link.get('href', '')
            
            # KSML:n artikkelit ovat muotoa /kulttuuri/{id} tai /paikalliset/{id}
            if '/kulttuuri/' in href or '/paikalliset/' in href:
                # Tarkista onko "Elokuva-arvio" lähellä
                parent = link.find_parent('article') or link.find_parent('div', class_='article')
                if parent:
                    text_content = parent.get_text()
                    if 'Elokuva-arvio' in text_content:
                        title = link.get_text(strip=True)
                        url = href
                        
                        # Muodosta absoluuttinen URL
                        if url.startswith('/'):
                            url = 'https://www.ksml.fi' + url
                        
                        reviews.append({
                            'title': title,
                            'url': url
                        })
                        
                        if len(reviews) >= limit:
                            break
        
        return reviews
    
    def _fetch_url(self, url: str) -> str:
        """Hakee URL:n sisällön."""
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        return response.text


class MetaScraper:
    """
    Pääorchestraattori joka koordinoi arvostelujen löytämistä.
    
    Yhdistää category crawlerin ja yksittäisten arvostelujen scrapauksen.
    """
    
    def __init__(self):
        self.category_crawler = CategoryCrawler()
    
    def discover_new_reviews(self, source: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Löytää uudet arvostelut lähteestä.
        
        Args:
            source: Lähteen tunniste ('sk', 'ts', 'il', 'ksml')
            limit: Montako max arvostelua etsitään
            
        Returns:
            Lista arvosteluja: [{'title': '...', 'url': '...'}]
        """
        print(f"🔍 Etsitään arvosteluja lähteestä: {source.upper()}")
        
        reviews = self.category_crawler.find_review_links(source, limit)
        
        print(f"✅ Löytyi {len(reviews)} arvostelua")
        
        return reviews
    
    def preview_discoveries(self, source: str, count: int = 5):
        """Näyttää preview löydetyistä arvosteluista."""
        reviews = self.discover_new_reviews(source, limit=count)
        
        print(f"\n📰 {source.upper()} - Uusimmat arvostelut:\n")
        
        for i, review in enumerate(reviews, 1):
            print(f"{i}. {review['title'][:70]}...")
            print(f"   🔗 {review['url']}")
            print()


# Esimerkki käytöstä
if __name__ == '__main__':
    print("=" * 60)
    print("METASCRAPER - Arvostelujen etsintä")
    print("=" * 60)
    print()
    
    meta = MetaScraper()
    
    # Testaa kaikki lähteet
    for source in ['ts', 'il', 'ksml', 'sk']:
        try:
            print(f"\n{'='*60}")
            meta.preview_discoveries(source, count=3)
        except Exception as e:
            print(f"❌ Virhe lähteessä {source}: {e}")
    
    print("\n💡 Käyttö:")
    print("   from discovery import MetaScraper")
    print("   meta = MetaScraper()")
    print("   reviews = meta.discover_new_reviews('ts', limit=10)")
    print()
