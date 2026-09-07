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
        # Luetaan koko endnote-kappale, koska esitystiedot ovat toisinaan eri
        # palasessa kuin endnote-merkintä.
        endnote_paragraph = self._get_endnote_paragraph_text(asset_data).lower()
        has_theater_in_endnote = any(
            kw in endnote or kw in endnote_paragraph for kw in theater_keywords
        )
        
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
        for section in reversed(self._paragraph_sections(asset_data)):
            endnote_parts = []
            for crumb in section.get('crumbs', []):
                if 'endnote' in crumb.get('marks', []):
                    content = crumb.get('content', '')
                    if content:
                        endnote_parts.append(content)
            if endnote_parts:
                return self.clean_text(''.join(endnote_parts)) or ''
        return ""

    def _get_endnote_paragraph_text(self, asset_data: dict) -> str:
        """Palauttaa koko sen kappaleen tekstin, jossa endnote on.

        Elokuvan nimi on toisinaan kursivoituna omassa palasessaan, jolloin
        siitä puuttuu endnote-merkintä: "Presidentin kyyditys" + ", ensi-ilta
        pe elokuvateattereissa. Komedia ★★★". Pelkkiä endnote-palasia
        lukemalla nimi jää saamatta.
        """
        for section in reversed(self._paragraph_sections(asset_data)):
            crumbs = section.get('crumbs', [])
            if not any('endnote' in crumb.get('marks', []) for crumb in crumbs):
                continue
            parts = [crumb.get('content', '') for crumb in crumbs]
            text = self.clean_text(''.join(parts))
            if text:
                return text
        return ""

    def _paragraph_sections(self, asset_data: dict) -> list:
        """Kappaleet järjestyksessä, mainospaikat ja tiivistelmät pois."""
        return [
            section for section in asset_data.get('splitBody', [])
            if section.get('type') == 'paragraph'
        ]

    def _get_full_text(self, asset_data: dict) -> str:
        """Palauttaa artikkelin koko tekstin yhtenä stringinä."""
        ingress = asset_data.get('ingress', '')
        title = asset_data.get('title', '')

        text_parts = [title, ingress]

        for section in self._paragraph_sections(asset_data):
            for crumb in section.get('crumbs', []):
                text_parts.append(crumb.get('content', ''))

        return ' '.join(text_parts)

    # --- Elokuvan nimen poiminta -------------------------------------------

    # Lajityyppisanat joilla IS päättää arvionsa: "Komedia ★★★".
    # Näistä koostuva pätkä ei ole elokuvan nimi.
    GENRE_WORDS = {
        'ja', 'sekä',
        'animaatio', 'biografia', 'dokumentti', 'draama', 'elokuva',
        'elämäkerta', 'fantasia', 'farssi', 'historiallinen', 'jännitys',
        'jännäri', 'kauhu', 'komedia', 'lastenelokuva', 'musikaali',
        'musta', 'mysteeri', 'perhe-elokuva', 'psykologinen', 'rikos',
        'romanssi', 'romanttinen', 'satiiri', 'scifi', 'seikkailu',
        'sci-fi', 'sota', 'toiminta', 'trilleri', 'tieteiselokuva', 'western',
    }

    # Yhdyssanaloppuja: "draamakomedia", "toimintaelokuva", "kauhutrilleri"
    GENRE_SUFFIXES = (
        'animaatio', 'dokumentti', 'draama', 'elokuva', 'fantasia',
        'jännäri', 'kauhu', 'komedia', 'musikaali', 'romanssi',
        'satiiri', 'trilleri',
    )

    # Kappaleet joissa nimi tavataan mainita kursiivilla
    ITALIC_LOOKUP_PARAGRAPHS = 6

    def _looks_like_genre(self, text: str) -> bool:
        """Onko pätkä lajityyppi ("Komedia", "Musta komedia") eikä nimi?"""
        cleaned = re.sub(r'[^\w\s-]', ' ', (text or '').lower())
        words = [word for word in cleaned.split() if word]
        if not words:
            return True

        for word in words:
            if word in self.GENRE_WORDS:
                continue
            if len(words) <= 2 and word.endswith(self.GENRE_SUFFIXES):
                continue
            return False
        return True

    def _clean_title_candidate(self, text: Optional[str]) -> Optional[str]:
        """Siivoaa ehdokkaan ja hylkää selvät osumat ohi maalin."""
        candidate = self.clean_text(text)
        if not candidate:
            return None

        candidate = candidate.strip(' "\u201d\u201c\u00ab\u00bb\'')
        candidate = candidate.rstrip('.,:;–-').strip()
        candidate = re.sub(r'[★⭐]+', '', candidate).strip()

        if not candidate or len(candidate) > 60:
            return None
        if not re.search(r'[A-Za-zÀ-ÿ0-9]', candidate):
            return None
        if self._looks_like_genre(candidate):
            return None
        return candidate

    def _title_from_endnote(self, asset_data: dict) -> Optional[str]:
        """Nimi arvion loppuriviltä: "Nimi, ensi-ilta pe. Komedia ★★★"."""
        for endnote in (self._get_endnote_text(asset_data),
                        self._get_endnote_paragraph_text(asset_data)):
            if not endnote:
                continue

            match = re.search(r'^(.+?),\s+ensi-ilta', endnote)
            if match:
                candidate = self._clean_title_candidate(match.group(1))
                if candidate:
                    return candidate

            if '★' in endnote:
                match = re.search(r'^(.+?)\s+★', endnote)
                if match:
                    potential_title = match.group(1).strip()
                    # Pilkun jälkeinen osa on esitystietoa, ei nimeä
                    if ',' in potential_title:
                        potential_title = potential_title.split(',')[0]
                    candidate = self._clean_title_candidate(potential_title)
                    if candidate:
                        return candidate

        return None

    def _title_from_italics(self, asset_data: dict) -> Optional[str]:
        """Nimi alkukappaleiden kursiivista.

        IS kursivoi elokuvan nimen jutun alussa: "...Samuli Valkaman ohjaama
        draamakomedia Presidentin kyyditys todistaa toisin."
        """
        sections = self._paragraph_sections(asset_data)[:self.ITALIC_LOOKUP_PARAGRAPHS]

        for section in sections:
            crumbs = section.get('crumbs', [])
            paragraph_text = ''.join(crumb.get('content', '') for crumb in crumbs)
            # Ohita "Lue lisää:" -nostot, joissa kursiivi on toisen jutun nimi
            if paragraph_text.strip().lower().startswith('lue lisää'):
                continue

            for crumb in crumbs:
                marks = crumb.get('marks', [])
                if 'em' not in marks and 'italic' not in marks:
                    continue
                candidate = self._clean_title_candidate(crumb.get('content'))
                if candidate:
                    return candidate

        return None

    def _title_from_headlines(self, asset_data: dict) -> Optional[str]:
        """Nimi otsikosta tai metaotsikosta."""
        title = self.clean_text(asset_data.get('title', '')) or ''
        meta_title = self.clean_text(asset_data.get('metaTitle', '')) or ''

        patterns = (
            r'^Arvio[:\s]\s*(.+?)\s+[–-]',
            r'^Arvostelu[:\s]\s*(.+?)\s+[–-]',
            r'^(.+?)\s+-arvio',
            r'^(.+?)\s+-arvostelu',
        )

        for text in (meta_title, title):
            if not text:
                continue
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    candidate = self._clean_title_candidate(match.group(1))
                    if candidate:
                        return candidate

        # "Tällainen on Sisu 2 – moni olisi kateellinen"
        match = re.search(r'(?:Tällainen on|on)\s+(.+?)\s+[-–]', title)
        if match:
            movie_name = re.sub(r'\s+elokuva$', '', match.group(1).strip(),
                                flags=re.IGNORECASE)
            candidate = self._clean_title_candidate(movie_name)
            if candidate:
                return candidate

        if '–' in title:
            candidate = self._clean_title_candidate(title.split('–')[0])
            if candidate and len(candidate) <= 50:
                return candidate

        if title and len(title) <= 50:
            return self._clean_title_candidate(title)

        return None

    def _extract_movie_title(self, asset_data: dict) -> Optional[str]:
        """Poimii elokuvan nimen luotettavimmasta paikasta.

        Järjestys:
        1. Arvion loppurivi ("Nimi, ensi-ilta pe. Komedia ★★★")
        2. Alkukappaleiden kursiivi (loppurivillä on vain lajityyppi)
        3. Otsikko ja metaotsikko
        """
        return (
            self._title_from_endnote(asset_data)
            or self._title_from_italics(asset_data)
            or self._title_from_headlines(asset_data)
        )

    def _extract_rating(self, asset_data: dict) -> Optional[int]:
        """
        Poimii tähtiarvion arvostelun lopusta.
        IS.fi muoto: "Genre ★★★" tai "Toiminta ★★"
        """
        for text in (self._get_endnote_text(asset_data),
                     self._get_endnote_paragraph_text(asset_data)):
            stars = self.count_stars(text or '')
            if stars:
                return stars

        # Tähdet voivat olla myös ilman endnote-merkintää viimeisissä
        # kappaleissa
        for section in reversed(self._paragraph_sections(asset_data)[-3:]):
            text = ''.join(crumb.get('content', '') for crumb in section.get('crumbs', []))
            stars = self.count_stars(text)
            if stars:
                return stars

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

