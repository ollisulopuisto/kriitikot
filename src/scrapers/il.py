"""
Iltalehti (IL.fi) movie review scraper.
"""

import json
import re
from typing import Optional
from bs4 import BeautifulSoup
from .base import Review


class ILScraper:
    """Scraper Iltalehden elokuva-arvosteluille."""
    
    def __init__(self):
        self.publication_name = 'Iltalehti'
    
    def parse_html(self, html_content: str, source_url: Optional[str] = None) -> Optional[Review]:
        """Parsii Iltalehden arvostelun."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # VALIDOINTI: Varmista että otsikossa on "IL-arvio"
        h1 = soup.find('h1')
        if not h1 or 'IL-arvio' not in h1.get_text():
            return None  # Ei ole IL-arvio, vaan joku muu juttu
        
        # Iltalehti käyttää yksinkertaista rakennetta
        title = self._extract_title(soup)
        author = self._extract_author(soup)
        rating = self._extract_rating(html_content, soup)
        review_text = self._extract_review_text(soup)
        
        if not title:
            return None
        
        return Review(
            movie_title=title,
            critic_name=author or 'Unknown',
            rating_stars=rating,
            review_text=review_text,
            source_url=source_url,
            source_publication=self.publication_name,
            raw_data={}
        )
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Poimii otsikon."""
        # h1 tag
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
            
            # Poista "IL-arvio: " prefix jos löytyy
            title = re.sub(r'^IL-arvio:\s*', '', title, flags=re.I)
            
            # Poista tähdet otsikosta
            title = re.sub(r'[⭐★]+', '', title).strip()
            
            return title
        
        return None
    
    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Poimii kirjoittajan nimen."""
        # Etsi author/byline elementit
        author_elem = soup.find(class_=re.compile(r'author|byline', re.I))
        if author_elem:
            author = author_elem.get_text(strip=True)
            
            # Poista aikaleima (esim. "Juho Rissanenlauantai 30.3.2024 klo 15:35")
            # Etsi viikonpäivä ja poista kaikki sen jälkeen
            match = re.search(r'^(.+?)(?:maanantai|tiistai|keskiviikko|torstai|perjantai|lauantai|sunnuntai)', author, re.I)
            if match:
                return match.group(1).strip()
            
            # Jos ei viikonpäivää, etsi päivämäärä (dd.mm.yyyy)
            match = re.search(r'^(.+?)(?:\d{1,2}\.\d{1,2}\.\d{4})', author)
            if match:
                return match.group(1).strip()
            
            return author
        
        return None
    
    def _extract_rating(self, html_content: str, soup: BeautifulSoup) -> Optional[int]:
        """Poimii tähtiarvion (1-5)."""
        # Iltalehti käyttää muotoa "IL-arvio: ⭐⭐⭐"
        # Etsi tämä pattern suoraan HTML:stä (ei parsitusta soup:sta)
        pattern = re.search(r'IL-arvio:\s*([⭐★]{1,5})', html_content)
        if pattern:
            stars = pattern.group(1)
            return len(stars)
        
        return None
    
    def _extract_review_text(self, soup: BeautifulSoup) -> Optional[str]:
        """Poimii arvostelutekstin."""
        # Etsi lead-teksti
        lead_elem = soup.find(class_=re.compile(r'lead|ingress|summary', re.I))
        if lead_elem:
            return lead_elem.get_text(strip=True)
        
        # Fallback: meta description
        meta_desc = soup.find('meta', property='og:description')
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content']
        
        return None
    
    def parse_file(self, file_path: str) -> Optional[Review]:
        """Parsii tiedostosta."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.parse_html(content)
        except (IOError, OSError):
            return None
