"""
Ilta-Sanomat (IS.fi) movie review scraper.
"""

import json
import re
from typing import Optional
from bs4 import BeautifulSoup
from .base import Review


class ISScraper:
    """Ilta-Sanomien arvostelujen parsija."""
    
    def __init__(self):
        self.publication_name = "Ilta-Sanomat"
    
    def parse_html(self, html_content: str, source_url: Optional[str] = None) -> Optional[Review]:
        """
        Parsii IS.fi:n HTML-sisällön ja palauttaa Review-objektin.
        
        IS.fi-arviot ovat tagilla "TV-lehti" ja sisältävät:
        - "Tv-lehti arvioi:" tekstin alussa
        - Arvion lopussa muodossa: "Genre ★★★" tai "Genre ★★"
        
        Args:
            html_content: HTML-sisältö merkkijonona
            source_url: Alkuperäinen URL (valinnainen)
            
        Returns:
            Review-objekti tai None jos parsiminen epäonnistuu tai ei ole arvio
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
        
        # Tarkista onko kyseessä elokuva-arvio (täytyy sisältää "TV-lehti" tag)
        if not self._is_movie_review(asset_data):
            return None
        
        # Pura tiedot
        movie_title = self._extract_movie_title(asset_data)
        if not movie_title:
            return None
            
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
            return data['props']['pageProps']['page']['assetData']
        except (KeyError, TypeError):
            return None
    
    def _is_movie_review(self, asset_data: dict) -> bool:
        """
        Tarkistaa onko artikkeli elokuva-arvio.
        IS.fi merkitsee arviot "TV-lehti" ja "Arviot" tageilla.
        
        HUOM: Hylkää arvostelut jotka koskevat vain suoratoistoa/TV:tä.
        Hyväksytään vain elokuvateattereissa esitettävät elokuvat.
        """
        # TARKISTUS 0: Jos metaTitle tai Title sisältää "-arvio", se on aina arvio!
        # Tämä ohittaa suoratoisto/teatteri-tarkistuksen, koska jos otsikossa on
        # nimenomaan mainittu se arvioksi, se on relevantti.
        meta_title = asset_data.get('metaTitle', '')
        title = asset_data.get('title', '')
        
        if '-arvio' in meta_title or 'Arvio:' in meta_title:
            return True
        if '-arvio' in title or 'Arvio:' in title:
            return True

        tags = asset_data.get('tags', [])
        tag_keys = [tag.get('key', '').lower() for tag in tags]
        
        # Vaadi että on "TV-lehti" JA "arviot" tag
        if not ('tv-lehti' in tag_keys and 'arviot' in tag_keys):
            return False
        
        # Tarkista ettei ole pelkkä suoratoisto/TV-arvostelu
        # Hyväksytään vain jos mainitaan "elokuvateatter" tai "valkokangas"
        text_content = self._get_full_text(asset_data).lower()
        
        # Suoratoistopalvelut ja TV-viittaukset jotka HYLÄTÄÄN
        streaming_keywords = [
            'katsomo+', 'katsomo +', 'mtv katsomo',
            'netflix', 'hbo', 'disney+', 'viaplay', 'ruutu',
            'suoratoistossa', 'suoratoistopalvelu',
            'tv:ssä', 'televisiossa',
            'tv-ensi-ilta', 'televisioensi-ilta'
        ]
        
        # Elokuvateatteriviittaukset jotka HYVÄKSYTÄÄN
        theater_keywords = [
            'elokuvateatter', 'valkokangas', 'teattereissa',
            'elokuvakino', 'finnkino'
        ]
        
        # Ensi-ilta on erikoistapaus: se voi olla myös tv-ensi-ilta
        # Poistetaan tekstistä tv-ensi-illat ennen tarkistusta
        clean_text_for_premiere_check = text_content \
            .replace('tv-ensi-ilta', '') \
            .replace('televisioensi-ilta', '')
            
        has_premiere = 'ensi-ilta' in clean_text_for_premiere_check
        
        # Jos mainitaan suoratoisto MUTTA EI teatteria → hylkää
        has_streaming = any(kw in text_content for kw in streaming_keywords)
        has_theater_keyword = any(kw in text_content for kw in theater_keywords)
        
        # Hyväksytään jos on teatterisana TAI (aito) ensi-ilta
        has_theater = has_theater_keyword or has_premiere
        
        if has_streaming and not has_theater:
            return False  # Pelkkä suoratoistoarvostelu
        
        return True
    
    def _get_full_text(self, asset_data: dict) -> str:
        """Palauttaa artikkelin koko tekstin yhtenä stringinä."""
        split_body = asset_data.get('splitBody', [])
        ingress = asset_data.get('ingress', '')
        title = asset_data.get('title', '')
        
        text_parts = [title, ingress]
        
        for section in split_body:
            if section.get('type') == 'paragraph':
                crumbs = section.get('crumbs', [])
                for crumb in crumbs:
                    text_parts.append(crumb.get('content', ''))
        
        return ' '.join(text_parts)
    
    def _extract_movie_title(self, asset_data: dict) -> Optional[str]:
        """
        Poimii elokuvan nimen otsikosta.
        IS.fi otsikot usein muodossa: "Tällainen on [Elokuva] – ..."
        Tai JSON-datasta voi löytyä suoraan elokuvan nimi theme_tagseista.
        """
        title = asset_data.get('title', '')
        meta_title = asset_data.get('metaTitle', '')
        
        # 0) Priority: Check metaTitle for "[Movie] -arvio" pattern
        # IS meta titles often have format: "MovieName -arvio: Subtitle"
        if meta_title:
            match = re.search(r'^(.+?)\s+-arvio', meta_title)
            if match:
                return match.group(1).strip()
        
        # Yritä poimia elokuvan nimi – patterns:
        # 1) "Sisu 2 -arvio:"
        # 2) "Tällainen on Sisu 2 –"
        # 3) Title suoraan jos lyhyt
        
        # Pattern 1: "[Elokuva] -arvio" tai "[Elokuva] – "
        match = re.search(r'(?:Tällainen on|on)\s+(.+?)\s+[-–]', title)
        if match:
            movie_name = match.group(1).strip()
            # Poista "elokuva" sana jos lopussa
            movie_name = re.sub(r'\s+elokuva$', '', movie_name, flags=re.IGNORECASE)
            return movie_name
        
        # Jos ei löydy, yritä ottaa kaikki ennen ensimmäistä "–" tai "-"
        if '–' in title:
            parts = title.split('–')
            potential_title = parts[0].strip()
            # Varmista että ei ole liian pitkä (max 50 merkkiä)
            if len(potential_title) <= 50:
                return potential_title
        
        # Fallback: käytä koko otsikkoa jos lyhyt
        if len(title) <= 50:
            return title
            
        return None
    
    def _extract_rating(self, asset_data: dict) -> Optional[int]:
        """
        Poimii tähtiarvion arvostelun lopusta.
        IS.fi muoto: "Genre ★★★" tai "Toiminta ★★"
        """
        # Etsi splitBody-osiosta endnote-tyyppinen teksti
        split_body = asset_data.get('splitBody', [])
        
        for section in reversed(split_body):  # Käy läpi lopusta alkuun
            if section.get('type') == 'paragraph':
                crumbs = section.get('crumbs', [])
                for crumb in crumbs:
                    # Etsi "endnote" markilla varustettu teksti
                    if 'endnote' in crumb.get('marks', []):
                        text = crumb.get('content', '')
                        # Laske tähtien määrä
                        stars = text.count('★')
                        if stars > 0:
                            return min(stars, 5)  # Max 5 tähteä
        
        return None
    
    def _extract_review_text(self, asset_data: dict) -> Optional[str]:
        """
        Poimii arvostelun tekstin.
        Yhdistää kaikki kappaleet yhdeksi tekstiksi.
        """
        split_body = asset_data.get('splitBody', [])
        paragraphs = []
        
        for section in split_body:
            if section.get('type') == 'paragraph':
                crumbs = section.get('crumbs', [])
                text_parts = []
                for crumb in crumbs:
                    if crumb.get('type') in ('text', 'internalLink', 'personLink'):
                        content = crumb.get('content', '')
                        if content:
                            text_parts.append(content)
                
                if text_parts:
                    paragraph_text = ''.join(text_parts).strip()
                    if paragraph_text:
                        paragraphs.append(paragraph_text)
        
        return '\n\n'.join(paragraphs) if paragraphs else None
    
    def parse_file(self, file_path: str) -> Optional[Review]:
        """Lukee ja parsii HTML-tiedoston."""
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
        'is': ISScraper(),
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
