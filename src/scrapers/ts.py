"""
Turun Sanomat (TS.fi) movie review scraper.
"""

import json
import re
from typing import Optional
from bs4 import BeautifulSoup
from .base import Review, BaseScraper


class TSScraper(BaseScraper):
    """Scraper Turun Sanomien elokuva-arvosteluille."""
    
    def __init__(self):
        super().__init__('Turun Sanomat')
    
    def parse_html(self, html_content: str, source_url: Optional[str] = None) -> Optional[Review]:
        """Parsii Turun Sanomien arvostelun."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # TS käyttää selkeää rakennetta
        title = self._extract_title(soup)
        author = self._extract_author(soup, html_content)
        rating = self._extract_rating(html_content)
        review_text = self._extract_review_text(html_content, soup)
        
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
        """
        Poimii elokuvan nimen.
        Käyttää järjestyksessä:
        1. <p class="intro"> - sisältää pelkän elokuvan nimen (esim. "Bugonia.")
        2. h1 otsikko (parsitaan verbeillä)
        """
        # 1. <p class="intro"> - paras lähde, sisältää puhtaan elokuvan nimen
        intro_p = soup.find('p', class_='intro')
        if intro_p:
            title = intro_p.get_text(strip=True)
            # Poista mahdollinen piste lopusta
            title = title.rstrip('.')
            if title:
                return title
        
        # 2. h1 tag (fallback)
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
            
            # Poista "Elokuva-arvostelu |" tai vastaavat prefixit
            title = re.sub(r'^Elokuva-arvostelu\s*\|\s*', '', title, flags=re.I)
            
            # Poista kriitikon nimi jos se on otsikossa
            # Esim: "Emma Stone tekee loistoroolin..." -> ota vain ennen verbiä
            # Etsitään pattern: "[Nimi] tekee|on|olisi|vie|tarjoaa [kuvaus]"
            verb_patterns = [
                r'^(.+?)\s+(tekee|on|olisi|vie|tarjoaa|kertoo)\s+.*',
            ]
            for pattern in verb_patterns:
                match = re.search(pattern, title)
                if match:
                    # Tarkista onko ensimmäinen osa lyhyt (todennäköisesti elokuvan nimi)
                    first_part = match.group(1).strip()
                    # Jos alle 50 merkkiä ja ei piste, todennäköisesti elokuvan nimi
                    if len(first_part) < 50 and '.' not in first_part:
                        title = first_part
                        break
            
            return title
        
        return None
    
    def _extract_author(self, soup: BeautifulSoup, html_content: str) -> Optional[str]:
        """Poimii kirjoittajan nimen."""
        # 1. Open Graph article:author meta tag (luotettavin lähde)
        author_meta = soup.find('meta', property='article:author')
        if author_meta and author_meta.get('content'):
            author = author_meta['content'].strip()
            # Varmista ettei ole julkaisun nimi (esim. "Turun Sanomat")
            if author.lower() not in ('turun sanomat', 'ts'):
                return author

        # 2. JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            if script.string:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        auth = data.get('author')
                        if isinstance(auth, dict):
                            name = auth.get('name')
                            if name:
                                return name
                        elif isinstance(auth, str):
                            return auth
                except json.JSONDecodeError:
                    pass

        # 3. Spesifi author-elementti (TS käyttää tsv3-c-common-article__meta__author)
        author_p = soup.find('p', class_='tsv3-c-common-article__meta__author')
        if author_p:
            text = author_p.get_text(strip=True)
            if text:
                return text

        # 4. Yleiset author-selectorit (fallback)
        author_elem = soup.find(class_=re.compile(r'\bauthor\b', re.I))
        if author_elem:
            author = author_elem.get_text(strip=True)
            # Poista päivämäärä jos mukana
            author = re.sub(r'\d{1,2}\.\d{1,2}\.\d{4}.*$', '', author).strip()
            if author:
                return author

        return None
    
    def _extract_rating(self, html_content: str) -> Optional[int]:
        """Poimii tähtiarvion (1-5)."""
        # TS käyttää ★-symboleja
        stars_match = re.search(r'(★{1,5})', html_content)
        if stars_match:
            return len(stars_match.group(1))
        
        return None
    
    def _extract_review_text(self, html_content: str, soup: BeautifulSoup) -> Optional[str]:
        """Poimii arvostelutekstin."""
        # Etsi tekstin alku - TS:n arvostelut alkavat usein tietyllä tavalla
        # Etsitään ensimmäinen kappale jossa on yli 50 merkkiä
        
        # Yritä löytää article body
        article = soup.find('article') or soup.find('div', class_=re.compile(r'article|body', re.I))
        if article:
            # Etsi kaikki p-tagit
            paragraphs = article.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 50 and not text.startswith('Tämä sisältö'):
                    # HTML-entiteetit saatetaan näyttää kuten &#246; → ö
                    # BeautifulSoup puhdistaa ne automaattisesti
                    return text
        
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
