"""
Yleiskäyttöinen web scraper elokuva-arvosteluille.

Tukee useita lähteitä ja tarjoaa yhtenäisen rajapinnan eri sivustojen
arvostelujen parsimiseen.
"""

import json
import re
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup


class Review:
    """Yhtenäinen tietorakenne arvostelulle, riippumaton lähteestä."""
    
    def __init__(
        self,
        movie_title: str,
        critic_name: str,
        rating_stars: Optional[int] = None,
        review_text: Optional[str] = None,
        source_url: Optional[str] = None,
        source_publication: str = "Unknown",
        raw_data: Optional[Dict[str, Any]] = None
    ):
        self.movie_title = movie_title
        self.critic_name = critic_name
        self.rating_stars = rating_stars  # 1-5 tähteä tai None
        self.review_text = review_text
        self.source_url = source_url
        self.source_publication = source_publication
        self.raw_data = raw_data or {}
    
    def to_dict(self) -> dict:
        """Palauttaa arvostelun sanakirjana."""
        return {
            'movie_title': self.movie_title,
            'critic_name': self.critic_name,
            'rating_stars': self.rating_stars,
            'review_text': self.review_text,
            'source_url': self.source_url,
            'source_publication': self.source_publication
        }


class HSScraper:
    """Helsingin Sanomien arvostelujen parsija."""
    
    def __init__(self):
        self.publication_name = "Helsingin Sanomat"
    
    def parse_html(self, html_content: str, source_url: Optional[str] = None) -> Optional[Review]:
        """
        Parsii HS.fi:n HTML-sisällön ja palauttaa Review-objektin.
        
        Args:
            html_content: HTML-sisältö merkkijonona
            source_url: Alkuperäinen URL (valinnainen)
            
        Returns:
            Review-objekti tai None jos parsiminen epäonnistuu
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Etsi Next.js data-scripti
        next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
        if not next_data_script:
            return None
        
        try:
            data = json.loads(next_data_script.string)
        except json.JSONDecodeError:
            return None
        
        # Navigoi JSON-rakenteessa
        asset_data = self._extract_asset_data(data)
        if not asset_data:
            return None
        
        # Pura tiedot
        movie_title = self._extract_movie_title(asset_data)
        critic_name = asset_data.get('byLine', 'Unknown')
        rating_stars = self._extract_rating(asset_data)
        review_text = self._extract_review_text(asset_data)
        
        # URL joko parametrina tai asset_datasta
        url = source_url or asset_data.get('shareUrl')
        
        return Review(
            movie_title=movie_title,
            critic_name=critic_name,
            rating_stars=rating_stars,
            review_text=review_text,
            source_url=url,
            source_publication=self.publication_name,
            raw_data=asset_data
        )
    
    def _extract_asset_data(self, data: dict) -> Optional[dict]:
        """Kaivaa assetData-osion Next.js datasta."""
        try:
            page_props = data.get('props', {}).get('pageProps', {})
            page = page_props.get('page', {})
            return page.get('assetData', {})
        except (KeyError, TypeError):
            return None
    
    def _extract_movie_title(self, asset_data: dict) -> str:
        """
        Poimii elokuvan nimen otsikosta.
        HS käyttää muotoa: "Elokuva-arvio | Otsikko" tai pelkkä otsikko.
        """
        title = asset_data.get('title', 'Unknown Movie')
        
        # Poista "Elokuva-arvio |" -prefix jos löytyy
        if '|' in title:
            parts = title.split('|')
            title = parts[-1].strip()
        
        return title
    
    def _extract_rating(self, asset_data: dict) -> Optional[int]:
        """
        Etsii tähtiarvion arvostelusta.
        HS:ssä tähdet ovat splitBody-rakenteessa.
        """
        split_body = asset_data.get('splitBody', [])
        
        for item in split_body:
            if item.get('type') != 'paragraph':
                continue
            
            crumbs = item.get('crumbs', [])
            for crumb in crumbs:
                # Tarkista sekä 'content' että 'value' kentät
                text = crumb.get('content', '') or crumb.get('value', '')
                if not isinstance(text, str):
                    continue
                
                # Etsi tähtikuvioita (★)
                stars = text.count('★')
                if 1 <= stars <= 5:
                    return stars
        
        return None
    
    def _extract_review_text(self, asset_data: dict) -> Optional[str]:
        """Poimii arvostelun tekstin."""
        # Yksinkertainen versio: otetaan ingress
        ingress = asset_data.get('ingress', '')
        
        # Myöhemmin voidaan laajentaa keräämään koko leipäteksti splitBodystä
        return ingress if ingress else None
    
    def parse_file(self, file_path: str) -> Optional[Review]:
        """Avaa tiedoston ja parsii sen."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.parse_html(content)
        except (IOError, OSError):
            return None


# Yleinen rajapinta - helppo lisätä uusia sivustoja
def scrape_review(html_content: str, source: str = 'hs', source_url: Optional[str] = None) -> Optional[Review]:
    """
    Yleiskäyttöinen funktio arvostelujen parsimiseen.
    
    Args:
        html_content: HTML-sisältö merkkijonona
        source: Lähteen tunniste ('hs', 'il', 'yle', jne.)
        source_url: Alkuperäinen URL (valinnainen)
        
    Returns:
        Review-objekti tai None
    """
    scrapers = {
        'hs': HSScraper(),
        # Myöhemmin lisätään:
        # 'il': ILScraper(),
        # 'yle': YLEScraper(),
    }
    
    scraper = scrapers.get(source.lower())
    if not scraper:
        raise ValueError(f"Unknown source: {source}. Supported: {', '.join(scrapers.keys())}")
    
    return scraper.parse_html(html_content, source_url)


# Taaksepäin yhteensopivuus vanhan testin kanssa
def scrape_hs_review(file_path: str) -> dict:
    """
    DEPRECATED: Käytä mieluummin HSScraper.parse_file() tai scrape_review().
    Säilytetty vanhojen testien takia.
    """
    scraper = HSScraper()
    review = scraper.parse_file(file_path)
    
    if review:
        return review.to_dict()
    return {}
