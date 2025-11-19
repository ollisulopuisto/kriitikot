"""
Helsingin Sanomat (HS.fi) movie review scraper.
"""

import json
import re
from typing import Optional
from bs4 import BeautifulSoup
from .base import Review


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
        critic_name = self._normalize_critic_name(critic_name)
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
        Poimii elokuvan nimen splitBody-rakenteesta.
        HS:ssä elokuvan tiedot ovat kappaleen muodossa:
        - "Elokuvan nimi, ohjaus X. Y min. K-raja. ★★★★" (pilkku)
        - "Elokuvan nimi. Ohjaus X. Y min. K-raja. ★★★" (piste)
        
        HUOM: Elokuvan nimi on ENNEN ensimmäistä pilkkua tai pistettä.
        """
        split_body = asset_data.get('splitBody', [])
        
        # Etsi kappale jossa on tähtiä (★) - se sisältää elokuvan tiedot
        for item in split_body:
            if item.get('type') != 'paragraph':
                continue
            
            crumbs = item.get('crumbs', [])
            full_text = ''.join([c.get('content', '') for c in crumbs])
            
            # Jos löytyy tähtimerkintä, tämä on elokuvatietokappale
            if '★' in full_text:
                # Muoto voi olla:
                # "A Big Bold Beautiful Journey, ohjaus Brady Corbet. 143 min. K12. ★★★"
                # "Elokuvan nimi. Ohjaus X. Y min. ★★★★"
                
                # Elokuvan nimi on ENNEN ensimmäistä pilkkua TAI "ohjaus"/"Ohjaus" sanaa
                # (kumpi tulee ensin)
                
                # Etsi ensimmäinen pilkku
                comma_split = full_text.split(',', 1)
                
                # Etsi "ohjaus" tai "Ohjaus"
                ohjaus_match = re.split(r'\s+[Oo]hjaus', full_text, maxsplit=1)
                
                # Käytä sitä mikä antaa lyhyemmän tuloksen (= tulee ensin)
                candidates = []
                
                if len(comma_split) > 1:
                    candidates.append(comma_split[0].strip())
                
                if len(ohjaus_match) > 1:
                    # Poista mahdollinen pilkku tai piste ennen "ohjaus"-sanaa
                    title = ohjaus_match[0].strip().rstrip('.,').strip()
                    candidates.append(title)
                
                # Valitse lyhyin (ensimmäinen erottelumerkki)
                if candidates:
                    title = min(candidates, key=len)
                    if title and len(title) > 2:
                        return title
        
        # Fallback: Käytä otsikkoa ja poista "Elokuva-arvio |" -prefix
        title = asset_data.get('title', 'Unknown Movie')
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

    def _normalize_critic_name(self, name: str) -> str:
        """Normalize critic name by removing trailing publication suffixes like 'HS' or 'Helsingin Sanomat'.

        Examples handled:
        - 'Mikko-Pekka Heikkinen HS' -> 'Mikko-Pekka Heikkinen'
        - 'Mikko-Pekka Heikkinen, HS' -> 'Mikko-Pekka Heikkinen'
        - 'Mikko-Pekka Heikkinen Helsingin Sanomat' -> 'Mikko-Pekka Heikkinen'
        """
        if not name or not isinstance(name, str):
            return name

        # Remove common trailing publication markers
        original = name
        name = re.sub(r"\s*(?:,)?\s*(?:HS|Helsingin\s+Sanomat)\s*$", "", name, flags=re.IGNORECASE)
        name = name.strip()
        return name if name else original.strip()
    
    def parse_file(self, file_path: str) -> Optional[Review]:
        """Avaa tiedoston ja parsii sen."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.parse_html(content)
        except (IOError, OSError):
            return None
