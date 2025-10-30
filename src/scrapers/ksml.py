"""
Keskisuomalainen (KSML.fi) movie review scraper.
"""

import json
import re
from typing import Optional
from bs4 import BeautifulSoup
from .base import Review


class KSMLScraper:
    """Keskisuomalaisen (KSML.fi) arvostelujen parsija.
    
    Tukee maksumuurin takana olevia artikkeleita ja etsii tietoja
    HTML:stä, JSON-LD-metatiedoista sekä näkyvästä sisällöstä.
    """
    
    def __init__(self):
        self.publication_name = "Keskisuomalainen"
    
    def parse_html(self, html_content: str, source_url: Optional[str] = None) -> Optional[Review]:
        """
        Parsii KSML.fi:n HTML-sisällön.
        
        Etsii:
        - Otsikon (h1, meta og:title tai JSON-LD)
        - Kirjoittajan (byline, meta author tai JSON-LD)
        - Tähtiarvion (tekstistä "X/5 tähteä" tai JSON-LD reviewRating)
        - Arvostelutekstin (näkyvät kappaleet, JSON-LD articleBody)
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Yritä löytää JSON-LD metadata
        ld_json = self._extract_json_ld(soup)
        
        # Poiminta
        title = self._extract_title(soup, ld_json)
        author = self._extract_author(soup, ld_json)
        rating = self._extract_rating(soup, ld_json)
        review_text = self._extract_review_text(soup, ld_json)
        
        if not title:
            return None
        
        return Review(
            movie_title=title,
            critic_name=author or 'Unknown',
            rating_stars=rating,
            review_text=review_text,
            source_url=source_url,
            source_publication=self.publication_name,
            raw_data=ld_json or {}
        )
    
    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[dict]:
        """Etsii JSON-LD structured data."""
        for script in soup.find_all('script', {'type': 'application/ld+json'}):
            try:
                data = json.loads(script.string or '{}')
                
                # Jos lista, etsi NewsArticle/Article
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') in ('NewsArticle', 'Article', 'Review'):
                            return item
                
                # Jos dict ja oikea tyyppi
                if isinstance(data, dict) and data.get('@type') in ('NewsArticle', 'Article', 'Review'):
                    return data
            except json.JSONDecodeError:
                continue
        
        return None
    
    def _extract_title(self, soup: BeautifulSoup, ld_json: Optional[dict]) -> Optional[str]:
        """
        Poimii otsikon.
        Käyttää järjestyksessä:
        1. <meta name="description"> - KSML käyttää tätä pelkälle elokuvan nimelle
        2. JSON-LD headline
        3. h1
        4. og:title
        5. <title>
        """
        title = None
        
        # 1. <meta name="description"> - KSML:llä usein pelkkä elokuvan nimi
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            desc = meta_desc['content'].strip()
            # Jos description on lyhyt (< 50 merkkiä), se on todennäköisesti elokuvan nimi
            if desc and len(desc) < 50 and not desc.startswith('Elokuva'):
                return desc
        
        # 2. Yritä JSON-LD
        if ld_json:
            title = ld_json.get('headline') or ld_json.get('name')
        
        # 3. Fallback: h1
        if not title:
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)
        
        # 4. Fallback: meta og:title
        if not title:
            meta_og = soup.find('meta', property='og:title')
            if meta_og and meta_og.get('content'):
                title = meta_og['content']
        
        # 5. Fallback: <title>
        if not title and soup.title:
            title = soup.title.string.strip() if soup.title.string else None
        
        # Puhdista: poista "Elokuva-arvio |" prefix
        if title:
            # Poista "Elokuva-arvio |" tai vastaavat
            if '|' in title:
                parts = title.split('|', 1)  # Split vain ensimmäisestä |:sta
                # Ota viimeinen osa (varsinainen elokuvan nimi)
                title = parts[-1].strip()
            
            # Poista "-ohjaajan" tai "-elokuvan" tyylinen teksti
            # Esim: "The Hurt Locker -ohjaajan A House of Dynamite" -> "A House of Dynamite"
            match = re.search(r'^.+?-(ohjaajan|elokuvan|tähden)\s+(.+)$', title)
            if match:
                title = match.group(2).strip()
            
            # Poista verbi-kuvaukset samalla tavalla kuin TS-scraperissa
            verb_patterns = [
                r'^(.+?)\s+(on|tarjoaa|kertoo|vie)\s+.*',
            ]
            for pattern in verb_patterns:
                match = re.search(pattern, title)
                if match:
                    first_part = match.group(1).strip()
                    if len(first_part) < 80 and '.' not in first_part:
                        title = first_part
                        break
            
            # Rajoita pituutta jos otsikko on epätavallisen pitkä
            if len(title) > 100:
                title = title[:100]
                # Etsi viimeinen välilyönti
                last_space = title.rfind(' ')
                if last_space > 50:
                    title = title[:last_space]
        
        return title
    
    def _extract_author(self, soup: BeautifulSoup, ld_json: Optional[dict]) -> Optional[str]:
        """Poimii kirjoittajan nimen."""
        author = None
        
        # JSON-LD
        if ld_json:
            auth = ld_json.get('author')
            if isinstance(auth, dict):
                author = auth.get('name')
            elif isinstance(auth, list) and auth:
                first = auth[0]
                if isinstance(first, dict):
                    author = first.get('name')
                elif isinstance(first, str):
                    author = first
        
        # Fallback: meta author
        if not author:
            meta_author = soup.find('meta', attrs={'name': 'author'})
            if meta_author and meta_author.get('content'):
                author = meta_author['content']
        
        # Fallback: common author selectors
        if not author:
            # Etsitään tyypillisiä author-luokkia
            author_elem = soup.select_one('[class*="author"], [class*="byline"], .article-author')
            if author_elem:
                author = author_elem.get_text(strip=True)
        
        # Puhdista: poista aikaleima jos mukana
        if author:
            # Poista "Tänään HH:MM" muoto
            author = re.sub(r'Tänään\s+\d{1,2}:\d{2}$', '', author)
            # Poista "Eilen HH:MM" muoto
            author = re.sub(r'Eilen\s+\d{1,2}:\d{2}$', '', author)
            # Poista "PP.KK.VVVV HH:MM" muoto
            author = re.sub(r'\d{1,2}\.\d{1,2}\.\d{4}\s+\d{1,2}:\d{2}$', '', author)
            # Poista pelkkä "HH:MM" jos esiintyy lopussa
            author = re.sub(r'\s+\d{1,2}:\d{2}$', '', author)
            author = author.strip()
        
        return author
    
    def _extract_rating(self, soup: BeautifulSoup, ld_json: Optional[dict]) -> Optional[int]:
        """
        Etsii tähtiarvion.
        KSML käyttää muotoa "Arvosana: 2/5 tähteä" tai vastaavaa.
        """
        rating = None
        
        # JSON-LD reviewRating
        if ld_json and 'reviewRating' in ld_json:
            try:
                rr = ld_json.get('reviewRating', {})
                val = rr.get('ratingValue')
                if isinstance(val, str):
                    # Etsi numero
                    match = re.search(r'(\d+)', val)
                    if match:
                        rating = int(match.group(1))
                elif isinstance(val, (int, float)):
                    rating = int(val)
            except Exception:
                pass
        
        # Fallback: etsi aria-label attribuutista
        if not rating:
            # KSML käyttää: <span role="img" aria-label="Arvosana: 2/5 tähteä">
            aria_elem = soup.find(attrs={'aria-label': re.compile(r'Arvosana:?\s*\d+/5', re.IGNORECASE)})
            if aria_elem:
                label = aria_elem.get('aria-label', '')
                match = re.search(r'(\d+)\s*/\s*5', label)
                if match:
                    rating = int(match.group(1))
        
        # Fallback: etsi tekstistä "X/5 tähteä" tai "Arvosana: X/5"
        if not rating:
            # Etsi koko sivulta
            text = soup.get_text()
            # Pattern: "2/5 tähteä" tai "Arvosana: 2/5"
            match = re.search(r'(?:Arvosana:?\s*)?(\d+)\s*/\s*5\s*tähteä', text, re.IGNORECASE)
            if match:
                rating = int(match.group(1))
        
        # Varmista että rating on 1-5
        if rating and not (1 <= rating <= 5):
            rating = None
        
        return rating
    
    def _extract_review_text(self, soup: BeautifulSoup, ld_json: Optional[dict]) -> Optional[str]:
        """Poimii arvostelutekstin."""
        text = None
        
        # JSON-LD
        if ld_json:
            text = ld_json.get('articleBody') or ld_json.get('description')
        
        # Fallback: etsi article-tagi
        if not text:
            article = soup.find('article')
            if article:
                paragraphs = [p.get_text(strip=True) for p in article.find_all('p') if p.get_text(strip=True)]
                if paragraphs:
                    text = '\n\n'.join(paragraphs)
        
        # Fallback: common content selectors
        if not text:
            content = soup.select_one('.article-body, .article__body, .content, .content-body')
            if content:
                paragraphs = [p.get_text(strip=True) for p in content.find_all('p') if p.get_text(strip=True)]
                if paragraphs:
                    text = '\n\n'.join(paragraphs)
                else:
                    text = content.get_text(strip=True)
        
        # Fallback: ensimmäinen p-tagi
        if not text:
            p = soup.find('p')
            if p:
                text = p.get_text(strip=True)
        
        return text if text else None
    
    def parse_file(self, file_path: str) -> Optional[Review]:
        """Avaa tiedoston ja parsii sen."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.parse_html(content)
        except (IOError, OSError):
            return None
