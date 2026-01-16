"""
Kaleva (kaleva.fi) movie review scraper.
"""

import json
import re
from typing import Optional
from bs4 import BeautifulSoup
from .base import Review, BaseScraper


class KalevaScraper(BaseScraper):
    """Kaleva.fi arvostelujen parsija."""
    
    def __init__(self):
        super().__init__("Kaleva")
    
    def parse_html(self, html_content: str, source_url: Optional[str] = None) -> Optional[Review]:
        """
        Parsii Kaleva.fi:n HTML-sisällön ja palauttaa Review-objektin.
        """
        soup = self.get_soup(html_content)
        
        # 1. Title
        # Prioritize extraction from article__intro (often contains "Name. Ohjaus: ...")
        intro_elem = soup.find(class_='article__intro')
        if intro_elem:
            intro_text = intro_elem.get_text().strip()
            # Common pattern: "Movie Name, Country Year. Ohjaus: Director."
            # Split by "Ohjaus" (case-insensitive)
            # Take the part before "Ohjaus"
            match = re.split(r'\s+[Oo]hjaus', intro_text, maxsplit=1)
            if len(match) > 1:
                potential_title = match[0].strip().rstrip(',.')
                # Sometimes there is country/year info at the end of this part. 
                # E.g. "Teräsleidit – kuin viimeistä päivää, Suomi 2025"
                # If we want to clean that, we could try. But the prompt just said "Teräsleidit – kuin viimeistä päivää"
                # so "Teräsleidit – kuin viimeistä päivää, Suomi 2025" might be acceptable or we might want to split by comma.
                # Let's keep the country/year for now if it's there as it's part of the identification, 
                # or try to split by last comma if it looks like a year?
                # The user example: "Teräsleidit – kuin viimeistä päivää, Suomi 2025." -> "Teräsleidit – kuin viimeistä päivää"
                # So we should probably split by comma if the comma part looks like "Country Year".
                
                # Simple heuristic: Split by last comma if present
                if ',' in potential_title:
                     parts = potential_title.rsplit(',', 1)
                     # Check if the last part looks like "Country Year" e.g. " Suomi 2025"
                     if re.search(r'\d{4}', parts[1]):
                         potential_title = parts[0].strip()
                
                movie_title = potential_title
            else:
                 # Fallback to headline extraction if intro doesn't match expected pattern
                 movie_title = self._extract_title_from_headline(soup)
        else:
            # Fallback to headline
            movie_title = self._extract_title_from_headline(soup)

        if not movie_title:
             return None

        # 2. Critic
        # <div class="article__page-info-author"> tai digitalData
        critic_name = "Unknown"
        
        # Yritetään digitalData scriptistä
        # digitalData = { ... "page": { "pageInfo": { "author": "Anssi Juntto", ... } } ... }
        dd_script = None
        for script in soup.find_all('script'):
            if script.string and 'digitalData =' in script.string:
                dd_script = script.string
                break
        
        if dd_script:
            try:
                # Etsitään authors: ["Nimi"] tai author: "Nimi"
                # Parsitaan regexillä json-objektia tai etsitään author kenttää
                match = re.search(r'"author":\s*"([^"]+)"', dd_script)
                if match:
                    critic_name = match.group(1)
            except Exception:
                pass
        
        if critic_name == "Unknown":
            # Fallback meta author
            meta_author = soup.find('meta', property='article:author')
            if meta_author:
                critic_name = meta_author.get('content')

        # 3. Rating
        # Etsitään <g class="svg-icon-star">
        # Usein tähdet on joko SVG-ikoneina tai tekstinä.
        # Testidatassa näkyi "svg-icon-star". Lasketaan montako löytyy "rating" tai vastaavan parentin alta?
        # Tai yksinkertaisesti lasketaan kaikki "svg-icon-star" esiintymät, mutta varotaan footerin tähtiä.
        # Yleensä arvostelun tähdet on alussa tai lopussa faktalaatikossa.
        
        rating_stars = None
        
        # Etsi faktalaatikko tai ingressi, jos tähdet on siellä
        # Kalevassa tähdet näyttää olevan SVG <use> tai <g> elementtejä.
        # Tarkistetaan onko ne spessu containerissa.
        # Katsotaan grep tuloksesta: <g class="svg-icon-star">
        
        stars = soup.find_all(class_='svg-icon-star')
        # Filtteröi pois mahdolliset navigaatio/footer tähdet jos niitä on.
        # Oletus: artikkelin sisällä on 1-5 tähteä peräkkäin.
        
        # Jos tähtiä on > 5, pitää keksiä logiikka.
        # Usein on "tähteä" teksti.
        if not stars:
             # Kokeillaan tekstihakua "X tähteä"
             text_content = soup.get_text()
             match = re.search(r'(\d+)\s+tähteä', text_content)
             if match:
                 rating_stars = int(match.group(1))
        else:
            # Lasketaan tähdet.
            # Varmistetaan että ne on nipussa.
            # Mutta yksinkertainen count voi toimia ensin.
            rating_stars = len(stars)
            if rating_stars > 5:
                # Ota vain 5 ekaa? Vai onko ne tuplana (täysi + tyhjä)?
                # Jos on 5 tähteä, voi olla 3 täyttä 2 tyhjää.
                # Tarkista 'fill' attribuutti tai class variantit jos testidata kertoo.
                # Kaleva esimerkki data ei paljastanut 'empty' classia vielä.
                # Oletan count toimii MVP:lle, säädetään testien perusteella.
                pass

        # 4. Review Text
        # <h2 class="article__lead"> on ingressi
        # Leipäteksti on usein paragraph elementeissä säiliössä.
        lead_elem = soup.find(class_='article__lead')
        review_text = lead_elem.get_text().strip() if lead_elem else ""
        
        # Lisää body text jos tarvetta, mutta base.py kommentti sanoi "ingressi riittää aluksi"
        
        # 5. Publication
        publication = self.publication_name
        
        # 6. URL
        url = source_url
        if not url:
            link = soup.find('link', rel='canonical')
            if link:
                url = link.get('href')

        return Review(
            movie_title=movie_title,
            critic_name=critic_name,
            rating_stars=rating_stars,
            review_text=review_text,
            source_url=url,
            source_publication=publication,
            raw_data={} 
        )

    def _extract_title_from_headline(self, soup: BeautifulSoup) -> Optional[str]:
        """Fallback: Extract title from headline."""
        title_elem = soup.find('h1', class_='article__headline')
        if title_elem:
            full_title = title_elem.get_text().strip()
            # Poistetaan "Arvio: " alkuosasta
            return re.sub(r'^Arvio:\s*', '', full_title, flags=re.IGNORECASE)
        
        # Fallback titleen
        title_tag = soup.find('title')
        if title_tag:
                full_title = title_tag.get_text().strip()
                movie_title = full_title.split('|')[0].strip()
                return re.sub(r'^Arvio:\s*', '', movie_title, flags=re.IGNORECASE)
        
        return None
