"""
Suomen Kuvalehti (SK.fi) movie review scraper.
"""

import re
from typing import Optional
from bs4 import BeautifulSoup
from .base import Review, BaseScraper


class SKScraper(BaseScraper):
    """Scraper Suomen Kuvalehden elokuva-arvosteluille."""
    
    def __init__(self):
        super().__init__('Suomen Kuvalehti')
    
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
        # 1. PRIORITY: Etsi täsmällinen muoto artikkelin lopusta
        # Muoto: "Ohjaaja: Elokuva. Elokuvateattereissa X.X. ★★★★★"
        # HUOM: Elokuvan nimessä voi olla kaksoispiste! (esim. "Chaos: The Manson Murders")
        # Esim: "Andrzej Żuławski: Possession. Elokuvateattereissa 3.10."
        # Esim: "Stanley Nelson: Chaos: The Manson Murders. Elokuvateattereissa 31.10."
        
        # Etsi kaikki <em> ja <p> tagit jotka ovat potentiaalisesti lopussa
        # SK:n tyyli on: "Ohjaaja: Elokuva. Jakelija/Alusta. ★★★★★"
        paragraphs = soup.find_all(['p', 'em'])
        
        # Lista tunnetuista jakelijoista/alustoista (case-insensitive myöhemmin)
        distributors = [
            r'Elokuvateattereissa', r'Netflix', r'HBO', r'Disney\+', r'Prime Video', 
            r'Apple TV\+', r'SkyShowtime', r'Viaplay', r'Yle Areena', r'Mubi', r'Max'
        ]
        distributors_pattern = '|'.join(distributors)
        
        for p in reversed(paragraphs):  # Käy läpi lopusta alkuun
            text = p.get_text(strip=True)
            
            # Etsitään muotoa "Ohjaaja: Elokuva. Jakelija."
            # Käytetään regexiä joka etsii lopusta tunnettua jakelijaa/alustaa
            # Regex selitys:
            # ^([A-ZÅÄÖ][A-Za-zÅÄÖåäö\s\-\.]+)  -> Ohjaajan nimi (alkaa isolla, voi sisältää väliviivoja/pisteitä)
            # :\s*                              -> Erotin ja välilyönnit
            # (.+?)                             -> Elokuvan nimi (non-greedy)
            # \.\s*                             -> Piste ja välilyönnit
            # (?:                               -> Jakelija ryhmä (non-capturing)
            #   Elokuvateattereissa|Netflix...  -> Vaihtoehdot
            # )
            
            pattern = r'^([A-ZÅÄÖ][A-Za-zÅÄÖåäö\s\-\.]+?):\s*(.+?)\.\s*(?:' + distributors_pattern + r')'
            
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                director = match.group(1).strip()
                title = match.group(2).strip()
                
                # Tarkistetaan että ohjaajan nimi on järkevä (max 5 sanaa)
                if len(director.split()) <= 5:
                    return title

        for p in reversed(paragraphs):
            text = p.get_text(strip=True)
            # 1.5 FALLBACK: Etsi muotoa "Elokuva. Jakelija." ilman ohjaajaa
            # Esim: "Hind Rajabin ääni. Elokuvateattereissa 30.1. ★★★"
            pattern_no_director = r'^(.+?)\.\s*(?:' + distributors_pattern + r')'
            match = re.search(pattern_no_director, text, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Varmistetaan ettei otsikko ole liian pitkä (ettei tule koko kappale)
                if len(title) < 100:
                    return title
        
        # 2. FALLBACK: Käytä og:title metatagia
        # SK:ssa meta og:title sisältää muodon "Arvio: [Arvosana] – [Elokuva] ..."
        # Esim: "Arvio: Neljä tähteä – Sisu 2 tarjoaa kaikkien aikojen..."
        # Esim: "Arvio: The Materialists nojaa perinteiseen hollywood-romantiikkaan"
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            title = meta_title['content']
            
            # Poista "Arvio:" prefix
            title = re.sub(r'^Arvio:\s*', '', title, flags=re.I)
            
            # Tarkista onko arvosana alussa (muoto: "Neljä tähteä – Elokuva")
            rating_pattern = r'^(Yksi|Kaksi|Kolme|Neljä|Viisi)\s+tähteä\s*[–-]\s*'
            title = re.sub(rating_pattern, '', title, flags=re.I)
            
            # Poista "The " prefix jos se on väärin (esim. "The Materialists" -> "Materialists")
            # MUTTA VAIN jos URL sisältää ilman "the":tä
            # Esim. URL: "/arvio-materialists-..." -> title: "The Materialists" -> poista "The "
            # Tämä on heuristiikka, ei aina oikein
            
            # Ota ensimmäinen osa ennen " on ", " – ", " ei " tai " tarjoaa " jne.
            for separator in [' nojaa ', ' tarjoaa ', ' on ', ' – ', ' ei ', ' kannatti ', ' osaa ']:
                if separator in title:
                    title = title.split(separator)[0].strip()
                    break
            
            # Poista mahdollinen "-elokuva" suffixi
            title = re.sub(r'\s*-elokuva$', '', title, flags=re.I)
            
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
        stars = self.count_stars(html_content)
        if stars:
            return stars
        
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
                if word in title and ('tähteä' in title or 'tähden' in title):
                    return num
        
        return None
    
    def _extract_review_text(self, soup: BeautifulSoup) -> Optional[str]:
        """Poimii arvostelutekstin."""
        # Etsi meta description
        meta_desc = self.meta_description(soup)
        if meta_desc:
            return meta_desc
        
        # Fallback: ensimmäinen p-tag artikkelista
        article = soup.find('article') or soup.find('div', class_=re.compile(r'article|content', re.I))
        if article:
            paragraphs = article.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 50:
                    return text
        
        return None
    
