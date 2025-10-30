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
        """Poimii otsikon."""
        title = None
        
        # Yritä JSON-LD
        if ld_json:
            title = ld_json.get('headline') or ld_json.get('name')
        
        # Fallback: h1
        if not title:
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)
        
        # Fallback: meta og:title
        if not title:
            meta_og = soup.find('meta', property='og:title')
            if meta_og and meta_og.get('content'):
                title = meta_og['content']
        
        # Fallback: <title>
        if not title and soup.title:
            title = soup.title.string.strip() if soup.title.string else None
        
        # Puhdista: poista "Elokuva-arvio |" prefix
        if title:
            # Poista "Elokuva-arvio |" tai vastaavat
            if '|' in title:
                parts = title.split('|', 1)  # Split vain ensimmäisestä |:sta
                # Ota viimeinen osa (varsinainen elokuvan nimi)
                title = parts[-1].strip()
            
            # Rajoita pituutta jos otsikko on epätavallisen pitkä
            if len(title) > 200:
                title = title[:200] + '...'
        
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
        
        # Puhdista: poista aikaleima jos mukana (esim. "Nimi15.10.2025 15:43")
        if author:
            # Etsi ensimmäinen numero-piste-numero (päivämäärän alku)
            match = re.search(r'^(.+?)(\d{1,2}\.\d{1,2}\.\d{4})', author)
            if match:
                author = match.group(1).strip()
        
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


class ILScraper:
    """Scraper Iltalehden elokuva-arvosteluille."""
    
    def __init__(self):
        self.publication_name = 'Iltalehti'
    
    def parse_html(self, html_content: str, source_url: Optional[str] = None) -> Optional[Review]:
        """Parsii Iltalehden arvostelun."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
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


class TSScraper:
    """Scraper Turun Sanomien elokuva-arvosteluille."""
    
    def __init__(self):
        self.publication_name = 'Turun Sanomat'
    
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
        """Poimii otsikon."""
        # h1 tag
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
            
            # Poista "Elokuva-arvostelu |" tai vastaavat prefixit
            title = re.sub(r'^Elokuva-arvostelu\s*\|\s*', '', title, flags=re.I)
            
            return title
        
        return None
    
    def _extract_author(self, soup: BeautifulSoup, html_content: str) -> Optional[str]:
        """Poimii kirjoittajan nimen."""
        # 1. Yritä meta property="article:author"
        author_meta = soup.find('meta', property='article:author')
        if author_meta and author_meta.get('content'):
            return author_meta['content']
        
        # 2. Etsi author-luokka
        author_elem = soup.find(class_=re.compile(r'author', re.I))
        if author_elem:
            author = author_elem.get_text(strip=True)
            # Poista päivämäärä jos mukana
            author = re.sub(r'\d{1,2}\.\d{1,2}\.\d{4}.*$', '', author).strip()
            if author:
                return author
        
        # 3. Etsi JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            if script.string:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        auth = data.get('author')
                        if isinstance(auth, dict):
                            return auth.get('name')
                        elif isinstance(auth, str):
                            return auth
                except json.JSONDecodeError:
                    pass
        
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


class SKScraper:
    """Scraper Suomen Kuvalehden elokuva-arvosteluille."""
    
    def __init__(self):
        self.publication_name = 'Suomen Kuvalehti'
    
    def parse_html(self, html_content: str, source_url: Optional[str] = None) -> Optional[Review]:
        """Parsii Suomen Kuvalehden arvostelun."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        title = self._extract_title(soup)
        author = self._extract_author(html_content, soup)
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
        """Poimii elokuvan nimen."""
        # SK:ssa meta og:title sisältää muodon "Arvio: [Elokuva] ..."
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            title = meta_title['content']
            
            # Poista "Arvio:" prefix
            title = re.sub(r'^Arvio:\s*', '', title, flags=re.I)
            
            # Ota ensimmäinen osa ennen " on " tai " – "
            if ' on ' in title:
                title = title.split(' on ')[0].strip()
            elif ' – ' in title:
                title = title.split(' – ')[0].strip()
            elif ' ei ' in title:
                title = title.split(' ei ')[0].strip()
            
            return title
        
        return None
    
    def _extract_author(self, html_content: str, soup: BeautifulSoup) -> Optional[str]:
        """Poimii kriitikon nimen."""
        # SK käyttää muotoa "[Nimi] kirjoittaa" tekstissä
        author_pattern = re.search(r'([A-ZÅÄÖ][a-zåäö]+\s+[A-ZÅÄÖ][a-zåäö]+)\s+kirjoittaa', html_content)
        if author_pattern:
            return author_pattern.group(1)
        
        return None
    
    def _extract_rating(self, html_content: str, soup: BeautifulSoup) -> Optional[int]:
        """Poimii tähtiarvion (1-5)."""
        # 1. Etsi ★-symbolit HTML:stä
        stars_match = re.search(r'(★{1,5})', html_content)
        if stars_match:
            return len(stars_match.group(1))
        
        # 2. Etsi sanallinen muoto meta og:title:stä
        # "Neljä tähteä", "Viisi tähteä" jne.
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            title = meta_title['content'].lower()
            
            numbers = {
                'yksi': 1, 'kaksi': 2, 'kolme': 3, 'neljä': 4, 'viisi': 5,
                'yhden': 1, 'kahden': 2, 'kolmen': 3, 'neljän': 4, 'viiden': 5
            }
            
            for word, num in numbers.items():
                if word in title and 'tähteä' in title or 'tähden' in title:
                    return num
        
        return None
    
    def _extract_review_text(self, soup: BeautifulSoup) -> Optional[str]:
        """Poimii arvostelutekstin."""
        # Etsi meta description
        meta_desc = soup.find('meta', property='og:description')
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content']
        
        # Fallback: ensimmäinen p-tag artikkelista
        article = soup.find('article') or soup.find('div', class_=re.compile(r'article|content', re.I))
        if article:
            paragraphs = article.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 50:
                    return text
        
        return None
    
    def parse_file(self, file_path: str) -> Optional[Review]:
        """Parsii tiedostosta."""
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
        'ksml': KSMLScraper(),
        'il': ILScraper(),
        'ts': TSScraper(),
        'sk': SKScraper(),
        # Myöhemmin lisätään:
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
