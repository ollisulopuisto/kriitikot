"""Muropaketti-scraper elokuva-arvosteluille."""
from .base import BaseScraper, Review
import re


class MuropakettiScraper(BaseScraper):
    """Scraper Muropaketti.com elokuva-arvosteluille.
    
    Muropaketti julkaisee elokuva-arvosteluja osoitteessa:
    https://muropaketti.com/kategoria/elokuvat/elokuva-arvostelut/
    
    Arvosana on kuvassa alt-tekstinä muodossa "Arvosana: X/5"
    """
    
    def __init__(self):
        super().__init__(publication_name="Muropaketti")
    
    def parse_html(self, html_content: str, source_url: str = None) -> Review:
        """Parsitaan Muropaketin elokuva-arvostelu.
        
        Args:
            html_content: HTML-sisältö merkkijonona
            source_url: Arvostelun URL (valinnainen)
            
        Returns:
            Review-olio
        """
        if source_url and not self._is_movie_review_url(source_url):
            # Muropaketti arvostelee myös pelejä, laitteita ja muuta,
            # esim. /pelit/peliarvostelut/..., eivätkä ne ole elokuvia.
            return None
        
        soup = self.get_soup(html_content)
        
        movie_title = self._extract_title(soup)
        critic_name = self._extract_critic(soup)
        rating_stars = self._extract_rating(soup)
        review_text = self._extract_text(soup)
        
        return Review(
            movie_title=movie_title,
            critic_name=critic_name,
            rating_stars=rating_stars,
            review_text=review_text,
            source_url=source_url,
            source_publication=self.publication_name
        )
    
    @staticmethod
    def _is_movie_review_url(source_url: str) -> bool:
        """Kertoo osoittaako URL Muropaketin elokuvaosioon."""
        return '/elokuvat/' in source_url

    def _extract_title(self, soup):
        """Etsi elokuvan nimi leipätekstistä.
        
        Elokuvan nimi on kappaleessa joka sisältää "Ensi-ilta:" ja muita tietoja.
        Nimi on tekstissä ennen "Ensi-ilta:" merkkijonoa.
        """
        # Etsi kaikki p-tagit
        paragraphs = soup.find_all('p')
        
        for p in paragraphs:
            text = p.get_text()
            # Etsi kappale jossa on "Ensi-ilta"
            if 'Ensi-ilta' in text:
                # Elokuvan nimi on ennen "Ensi-ilta:" tai "Ensi-ilta" tekstiä
                
                # 1. Kokeile löytää <strong> tagi kappaleen sisältä
                strong = p.find('strong')
                if strong:
                    title = strong.get_text().strip()
                else:
                    # 2. Fallback: splitataan tekstistä
                    # Käytään regexiä tai splitataan varovasti
                    if 'Ensi-ilta:' in text:
                        title = text.split('Ensi-ilta:', 1)[0].strip()
                    else:
                        title = text.split('Ensi-ilta', 1)[0].strip()

                if title:
                    # Poista mahdolliset kaksoispisteet lopusta
                    title = title.rstrip(':').strip()
                    
                    # Normalisoi isoista kirjaimista title caseen
                    # Jos nimi on kokonaan isoilla (sallien välimerkit ja numerot)
                    # Tai jos se on hyvin pitkä ja isoilla
                    if title.isupper() or (len(title) > 0 and title.replace(':', '').replace('-', '').replace(' ', '').isupper()):
                        # Muunna Title Caseen, mutta yritä säilyttää jotain järkeä
                        # Yksinkertainen title() toimii useimmiten tarpeeksi hyvin
                        title = title.title()
                        
                        # Korjaa pienet sanat jos tarpeen, mutta title() on hyvä alku
                        # Esim "Veitset Esiin" -> "Veitset esiin" olisi parempi suomeksi, 
                        # mutta geneerinen ratkaisu on vaikea. 
                        # "Wake Up Dead Man: Veitset Esiin -Mysteeri" on OK.
                    
                    return title
        
        # Fallback: käytä h1-otsikkoa
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text().strip()
            # Poista "Arvostelu  " etuliite (kaksi välilyöntiä)
            if title.startswith('Arvostelu  '):
                title = title[len('Arvostelu  '):]
            elif title.startswith('Arvio  '):
                title = title[len('Arvio  '):]
            return title
        
        return None
    
    def _extract_critic(self, soup):
        """Etsi kriitikon nimi meta-tagista."""
        author_meta = soup.find('meta', {'name': 'author'})
        if author_meta:
            return author_meta.get('content')
        return None
    
    def _extract_rating(self, soup):
        """Etsi tähtimäärä kuvan alt-tekstistä tai tiedostonimestä.
        
        Arvosana voi olla kahdessa muodossa:
        1. Kuvan alt-teksti: "Arvosana: X/5"
        2. Kuvan src/data-src tiedostonimi: "elokuva-arvostelu-tahdet-X.png"
           missä X voi olla: 05, 2, 25, 3, 35, 4, 45, 5
        """
        # Etsi kaikki kuvat
        images = soup.find_all('img')
        
        for img in images:
            # 1. Tarkista alt-teksti
            alt_text = img.get('alt', '')
            match = re.search(r'arvosana[:\s]+(\d+)/5', alt_text, re.IGNORECASE)
            if match:
                rating = int(match.group(1))
                if 1 <= rating <= 5:
                    return rating
            
            # 2. Tarkista tiedostonimi (src tai data-src)
            for attr in ['src', 'data-src']:
                src = img.get(attr, '')
                if 'arvostelu-tahdet' in src or 'elokuva-arvostelu-tahdet' in src:
                    # Etsi numero tiedostonimestä: tahdet-X.png
                    match = re.search(r'tahdet-(\d+(?:\d)?)', src)
                    if match:
                        rating_str = match.group(1)
                        # Muunna: 05 -> 0.5, 2 -> 2, 25 -> 2.5, 3 -> 3, jne.
                        if len(rating_str) == 1:
                            # Kokonaisluku: 2, 3, 4, 5
                            rating = int(rating_str)
                        elif len(rating_str) == 2:
                            # Puolikkaat: 05 -> 0.5, 25 -> 2.5, 35 -> 3.5, 45 -> 4.5
                            rating = int(rating_str[0]) + 0.5
                        
                        # Pyöristä kokonaisluvuksi (0.5 -> 1, 2.5 -> 3, jne.)
                        rating = round(rating)
                        
                        if 1 <= rating <= 5:
                            return rating
        
        return None
    
    def _extract_text(self, soup):
        """Etsi arvostelun leipäteksti.
        
        Teksti on artikkelin sisällä olevissa p-tageissa.
        """
        # Etsi entry-content tai vastaava div
        content_div = soup.find('div', class_=lambda x: x and 'entry-content' in str(x))
        
        if not content_div:
            # Fallback: etsi kaikki p-tagit
            content_div = soup
        
        paragraphs = content_div.find_all('p')
        text_parts = []
        
        for p in paragraphs:
            text = p.get_text(strip=True)
            # Ohita lyhyet kappaleet ja mainoslinkit
            if len(text) > 30 and not text.startswith('Lue myös'):
                text_parts.append(text)
        
        return ' '.join(text_parts) if text_parts else None
