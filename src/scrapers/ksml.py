"""
Keskisuomalainen (KSML.fi) movie review scraper.
"""

import re
from typing import Optional
from bs4 import BeautifulSoup
from .base import Review, BaseScraper


class KSMLScraper(BaseScraper):
    """Keskisuomalaisen (KSML.fi) arvostelujen parsija.
    
    Tukee maksumuurin takana olevia artikkeleita ja etsii tietoja
    HTML:stä, JSON-LD-metatiedoista sekä näkyvästä sisällöstä.
    """
    
    def __init__(self):
        super().__init__("Keskisuomalainen")
    
    def exclusion_reason(self, html_content: str) -> str | None:
        """Only known paywalled previews with film and byline may lack stars."""
        soup = self.get_soup(html_content)
        metadata = self._extract_json_ld(soup)
        if not metadata or metadata.get('isAccessibleForFree') is not False:
            return None
        if not self._extract_title(soup, metadata):
            return None
        author = self._extract_author(soup, metadata)
        if (not author or author.casefold() in {'unknown', 'tuntematon', 'ksml', 'keskisuomalainen'}
                or re.match(r'https?://', author, re.IGNORECASE)):
            return None
        # Malformed or unsupported rating markup is a parser problem, not absence.
        if (metadata.get('reviewRating') is not None
                or soup.find(attrs={'aria-label': re.compile(r'arvosana|/\s*5', re.IGNORECASE)})
                or re.search(r'[★☆⭐]|\b\d+\s*/\s*5\b', soup.get_text(' ', strip=True))):
            return None
        if self._extract_rating(soup, metadata) is None:
            return 'paywalled_unrated_preview'
        return None

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
        """Etsii JSON-LD structured datan (jaettu toteutus BaseScraperissa)."""
        return self.extract_jsonld(soup)
    
    def _extract_title(self, soup: BeautifulSoup, ld_json: Optional[dict]) -> Optional[str]:
        """
        Poimii elokuvan nimen vain film-facts storyline -kappaleesta.
        Ingressi, article headline and generic metadata are not film identity.
        """
        # Etsi spesifillä luokalla: diks-storyline__lead-paragraph.
        # Jutun rakenne on: ingressi, kirjoittaja, elokuvan nimi, tekijätiedot,
        # tähdet. Nimi on siis ensimmäinen storyline-kappale, ja se on
        # luotettavampi kuin meta-description, joka toistaa usein ingressin.
        for lead_p in soup.find_all('p', class_='diks-storyline__lead-paragraph'):
            text = lead_p.get_text(strip=True)
            if self._looks_like_movie_title(text):
                return self._pick_release_title(text, soup)

        return None

    @staticmethod
    def _looks_like_movie_title(text: Optional[str]) -> bool:
        """Erottaa elokuvan nimen ingressilauseesta ja tekijätiedoista."""
        if not text:
            return False
        
        text = text.strip()
        if len(text) < 2 or len(text) > 100:
            return False
        
        # Tekijätiedot: "Ohjaus Lauri Nurkse. Rooleissa: ..."
        if re.match(r'^(Ohjaus|Ohjaaja|Rooleissa|Käsikirjoitus|Teksti|Kuva|Arvio|Tähdet)\b', text):
            return False
        
        # Päivämäärä tai kellonaika
        if re.search(r'\d{1,2}\.\d{1,2}\.', text) or re.search(r'\d{1,2}:\d{2}', text):
            return False
        
        # Kokonainen lause, esim. "The Visitor tarkkailee enemmän kuin koskettaa."
        if text.endswith('.') and len(text.split()) > 2:
            return False
        
        return True

    @staticmethod
    def _pick_release_title(title: str, soup: BeautifulSoup) -> str:
        """Valitsee kaksiosaisesta nimestä sen, jota jutussa käytetään.
        
        KSML kirjoittaa vieraskielisistä elokuvista muodon
        "Svečias – The Visitor". Kumpi puoli on Suomessa käytetty nimi,
        selviää ingressistä: se mainitsee elokuvan sillä nimellä.
        Jos ingressi ei kerro, nimi jätetään sellaisenaan.
        """
        parts = [part.strip() for part in re.split(r'\s+[–—]\s+', title)]
        if len(parts) != 2 or not all(parts):
            return title
        
        lead = soup.find('p', class_='diks-article__lead')
        lead_text = lead.get_text(strip=True).lower() if lead else ''
        if not lead_text:
            return title
        
        matches = [part for part in parts if part.lower() in lead_text]
        if len(matches) == 1:
            return matches[0]
        
        return title

    def _extract_author(self, soup: BeautifulSoup, ld_json: Optional[dict]) -> Optional[str]:
        """Poimii kirjoittajan nimen."""
        author = None
        
        # 1. Open Graph article:author meta tag (luotettavin lähde KSML:llä)
        og_author = soup.find('meta', property='article:author')
        if og_author and og_author.get('content'):
            return og_author['content'].strip()
        
        # 2. JSON-LD
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
        
        # 3. meta name="author"
        if not author:
            meta_author = soup.find('meta', attrs={'name': 'author'})
            if meta_author and meta_author.get('content'):
                author = meta_author['content']
        
        # 4. Spesifi byline-selector (KSML käyttää diks-byline__author)
        if not author:
            byline_author = soup.find('p', class_='diks-byline__author')
            if byline_author:
                author = byline_author.get_text(strip=True)
        
        # 5. Yleiset author-selectorit (fallback)
        if not author:
            author_elem = soup.select_one('[class*="author"], [class*="byline"], .article-author')
            if author_elem:
                author = author_elem.get_text(strip=True)
        
        # Puhdista: poista aikaleima ja muu roska jos mukana
        if author:
            # Poista "| Päivitetty..." tai "| Päivitettytänään..." suffix
            author = re.sub(r'\s*\|\s*Päivitetty.*$', '', author)
            # Poista "Tänään HH:MM" / "Eilen HH:MM" / "PP.KK.VVVV HH:MM" suffixit
            author = re.sub(r'\s*(?:Tänään|Eilen)\s+\d{1,2}:\d{2}\b.*$', '', author)
            author = re.sub(r'\s*\d{1,2}\.\d{1,2}\.\d{4}\s+\d{1,2}:\d{2}\b.*$', '', author)
            # Poista pelkkä "HH:MM" lopussa
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
    
