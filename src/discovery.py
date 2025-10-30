"""
Discovery-moduuli: Löytää uudet elokuva-arvostelut automaattisesti.

Tämä moduuli sisältää "metascraperin" joka:
1. Crawlaa kategoriasivuja
2. Tunnistaa arvostelut
3. Palauttaa URL-listoja jatkokäsittelyä varten
"""

from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import requests
import re
from datetime import datetime


class CategoryCrawler:
    """Crawlaa kategoriasivuja ja löytää linkejä arvosteluihin."""
    
    # Kategoriasivut joilta arvostelut löytyvät
    CATEGORY_PAGES = {
        'sk': 'https://suomenkuvalehti.fi/avainsana/elokuva/',
        # Lisätään muut kun löydetään
        # 'hs': 'https://www.hs.fi/kulttuuri/elokuva/',
        # 'ksml': 'https://www.ksml.fi/kulttuuri/',
        # 'il': 'https://www.iltalehti.fi/tv-ja-leffat/',
        # 'ts': 'https://www.ts.fi/kulttuuri/',
    }
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def find_review_links(self, source: str, limit: int = 20) -> List[Dict[str, str]]:
        """
        Palauttaa arvostelu-URL:t kategoriasivulta.
        
        Args:
            source: Lähteen tunniste ('sk', 'hs', jne.)
            limit: Montako arvostelua max palautetaan
            
        Returns:
            Lista dictionaryja, joissa 'title' ja 'url'
        """
        url = self.CATEGORY_PAGES.get(source)
        if not url:
            raise ValueError(f"Unknown source: {source}")
        
        html = self._fetch_url(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Lähdekohtainen logiikka
        if source == 'sk':
            return self._find_sk_reviews(soup, limit)
        
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
            source: Lähteen tunniste ('sk', 'hs', jne.)
            limit: Montako max arvostelua etsitään
            
        Returns:
            Lista arvosteluja: [{'title': '...', 'url': '...'}]
        """
        print(f"🔍 Etsitään arvosteluja lähteestä: {source}")
        
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
    
    # Hae SK:n arvostelut
    meta.preview_discoveries('sk', count=5)
    
    print("\n💡 Käyttö:")
    print("   from discovery import MetaScraper")
    print("   meta = MetaScraper()")
    print("   reviews = meta.discover_new_reviews('sk', limit=10)")
    print()
