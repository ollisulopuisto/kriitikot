"""
Ilta-Sanomat (IS.fi) movie review scraper.
"""

import json
import re
from typing import Optional
from bs4 import BeautifulSoup
from .base import Review, BaseScraper


class ISScraper(BaseScraper):
    """Ilta-Sanomien arvostelujen parsija."""
    
    def __init__(self):
        super().__init__("Ilta-Sanomat")
    
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
        
        data = self.extract_next_data(soup)
        if not data:
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
        tags = asset_data.get('tags', [])
        tag_keys = [tag.get('key', '').lower() for tag in tags]
        
        # Vaadi että on "TV-lehti" JA "arviot" tag
        if not ('tv-lehti' in tag_keys and 'arviot' in tag_keys):
            return False
        
        endnote = self._get_endnote_text(asset_data).lower()
        text_content = self._get_full_text(asset_data).lower()
        
        # Suoratoistopalvelut ja TV-viittaukset jotka HYLÄTÄÄN
        streaming_keywords = [
            'katsomo+', 'katsomo +', 'mtv katsomo',
            'netflix', 'hbo', 'disney+', 'viaplay', 'ruutu',
            'suoratoistossa', 'suoratoistopalvelu',
            'tv:ssä', 'televisiossa',
            'tv-ensi-ilta', 'televisioensi-ilta',
            'yle areena', 'sky showtime', 'skyshowtime',
            'prime video', 'apple tv+', 'apple tv'
        ]
        
        # Elokuvateatteriviittaukset jotka HYVÄKSYTÄÄN
        theater_keywords = [
            'elokuvateatter', 'valkokangas', 'teattereissa',
            'elokuvakino', 'finnkino'
        ]
        
        # TV-kanava tai kello-viittaukset endnotessa (esim. "Teema & Fem klo 21.00")
        is_tv_schedule = bool(re.search(r'klo\s+\d{1,2}\.\d{2}', endnote))
        has_tv_channels = any(ch in endnote for ch in ['yle', 'teema', 'fem', 'mtv', 'nelonen', 'sub'])
        
        # Ensi-ilta on erikoistapaus: se voi olla myös tv-ensi-ilta
        # Poistetaan tekstistä tv-ensi-illat ennen tarkistusta
        clean_text_for_premiere_check = text_content \
            .replace('tv-ensi-ilta', '') \
            .replace('televisioensi-ilta', '')
            
        has_premiere = 'ensi-ilta' in clean_text_for_premiere_check
        
        # Jos endnotessa mainitaan teatteri, se on hyvä!
        has_theater_in_endnote = any(kw in endnote for kw in theater_keywords)
        
        # Jos mainitaan suoratoisto tai TV-aikataulu → vaadi teatteriviittaus
        has_streaming = any(kw in text_content for kw in streaming_keywords)
        
        if (has_streaming or is_tv_schedule or has_tv_channels) and not has_theater_in_endnote:
            return False  # Todennäköisesti TV/suoratoistoarvostelu
            
        # Jos ei ole mitään viittausta teatteriin eikä ole ensi-ilta, hylkää
        has_theater_anywhere = any(kw in text_content for kw in theater_keywords) or has_premiere
        
        if not has_theater_anywhere:
            return False
        
        return True
    
    def _get_endnote_text(self, asset_data: dict) -> str:
        """Kaivaa arvostelun lopussa olevan tiivistelmätekstin (endnote)."""
        split_body = asset_data.get('splitBody', [])
        for section in reversed(split_body):
            if section.get('type') == 'paragraph':
                crumbs = section.get('crumbs', [])
                endnote_parts = []
                for crumb in crumbs:
                    if 'endnote' in crumb.get('marks', []):
                        content = crumb.get('content', '')
                        if content:
                            endnote_parts.append(content)
                if endnote_parts:
                    return ''.join(endnote_parts).strip()
        return ""

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
        Poimii elokuvan nimen otsikosta tai endnotesta.
        IS.fi otsikot usein muodossa: "Tällainen on [Elokuva] – ..."
        Endnote muodossa: "[Elokuva], ensi-ilta..."
        """
        # 1) Try to find title from the "endnote" at the end of the body.
        # This is usually the most reliable place for the official title.
        endnote = self._get_endnote_text(asset_data)
        if endnote:
            # Pattern: "Title, ensi-ilta..."
            match = re.search(r'^(.+?),\s+ensi-ilta', endnote)
            if match:
                return match.group(1).strip()
            
            # Fallback if no "ensi-ilta" but stars: "Title ★★★"
            if '★' in endnote:
                # Take everything before the stars
                match = re.search(r'^(.+?)\s+★', endnote)
                if match:
                    potential_title = match.group(1).strip()
                    # Jos tittelissä on pilkku, ota vain alkuosa (vältä "Title, TV-kanava" tyyppiset)
                    if ',' in potential_title:
                        potential_title = potential_title.split(',')[0].strip()
                    return potential_title

        title = asset_data.get('title', '')
        meta_title = asset_data.get('metaTitle', '')
        
        # 2) Priority: Check metaTitle for movie title patterns
        if meta_title:
            match = re.search(r'^Arvio\s+(.+?)\s+[–-]', meta_title)
            if match:
                return match.group(1).strip()
            match = re.search(r'^(.+?)\s+-arvio', meta_title)
            if match:
                return match.group(1).strip()
        
        # Pattern: "Tällainen on Sisu 2 –"
        match = re.search(r'(?:Tällainen on|on)\s+(.+?)\s+[-–]', title)
        if match:
            movie_name = match.group(1).strip()
            movie_name = re.sub(r'\s+elokuva$', '', movie_name, flags=re.IGNORECASE)
            return movie_name
        
        if '–' in title:
            parts = title.split('–')
            potential_title = parts[0].strip()
            if len(potential_title) <= 50:
                return potential_title
        
        if len(title) <= 50:
            return title
            
        return None
    
    def _extract_rating(self, asset_data: dict) -> Optional[int]:
        """
        Poimii tähtiarvion arvostelun lopusta.
        IS.fi muoto: "Genre ★★★" tai "Toiminta ★★"
        """
        endnote = self._get_endnote_text(asset_data)
        if endnote:
            stars = endnote.count('★')
            if stars > 0:
                return min(stars, 5)
        
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

