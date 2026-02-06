"""
Episodi.fi scraper - käyttää WordPress JSON API:a
"""

from .base import BaseScraper, Review
from bs4 import BeautifulSoup
import requests
import json
from typing import List


class EpisodiScraper(BaseScraper):
    """Scraper for Episodi.fi movie reviews using JSON API."""
    
    def __init__(self):
        super().__init__(publication_name="Episodi")
        self.api_url = "https://www.episodi.fi/wp-json/wp/v2/elokuvat"
    
    def parse_html(self, html_content: str, source_url: str = None) -> Review:
        """Parse HTML and return Review object."""
        soup = self.get_soup(html_content)
        
        # Hae elokuvan nimi
        movie_title = self._extract_title(soup)
        
        # Hae kriitikon nimi
        critic_name = self._extract_critic(soup)
        
        # Hae tähtimäärä
        rating_stars = self._extract_rating(soup)
        
        # Hae arvosteluteksti
        review_text = self._extract_text(soup)
        
        return Review(
            movie_title=movie_title,
            critic_name=critic_name,
            rating_stars=rating_stars,
            review_text=review_text,
            source_url=source_url,
            source_publication=self.publication_name
        )
    
    def parse_json_api(self, limit: int = 20) -> List[Review]:
        """
        Hakee arvostelut suoraan JSON API:sta.
        
        Args:
            limit: Montako arvostelua max haetaan
            
        Returns:
            Lista Review-objekteja
        """
        reviews = []
        
        try:
            # Hae JSON-data (_embed-parametrilla saadaan kirjoittajan nimi suoraan)
            response = requests.get(
                self.api_url,
                params={'per_page': limit, 'orderby': 'date', 'order': 'desc', '_embed': '1'},
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # Parsitaan jokainen arvostelu
            for item in data:
                try:
                    # Hae elokuvan nimi
                    movie_title = item.get('title', {}).get('rendered', '').strip()
                    if not movie_title:
                        continue
                    
                    # Hae arvosteluteksti (excerpt tai content)
                    review_html = item.get('content', {}).get('rendered', '')
                    if review_html:
                        soup = BeautifulSoup(review_html, 'html.parser')
                        review_text = soup.get_text(strip=True, separator=' ')
                    else:
                        review_text = item.get('excerpt', {}).get('rendered', '')
                        if review_text:
                            soup = BeautifulSoup(review_text, 'html.parser')
                            review_text = soup.get_text(strip=True, separator=' ')
                    
                    # Hae kriitikon nimi (_embedded-datasta)
                    critic_name = "Episodi"  # Default
                    if '_embedded' in item and 'author' in item['_embedded']:
                        authors = item['_embedded']['author']
                        if authors and len(authors) > 0:
                            critic_name = authors[0].get('name', 'Episodi')
                    
                    # Hae tähtimäärä (custom field tai arvaa tekstistä)
                    rating_stars = self._extract_rating_from_json(item)
                    
                    # Hae URL
                    source_url = item.get('link', '')
                    
                    review = Review(
                        movie_title=movie_title,
                        critic_name=critic_name,
                        rating_stars=rating_stars,
                        review_text=review_text[:500] if review_text else "",
                        source_url=source_url,
                        source_publication=self.publication_name
                    )
                    
                    reviews.append(review)
                    
                except Exception as e:
                    print(f"  [Episodi] Virhe yksittäisen arvostelun parsinnassa: {e}")
                    continue
        
        except Exception as e:
            print(f"  [Episodi] JSON API virhe: {e}")
        
        return reviews
    
    def _extract_rating_from_json(self, item: dict) -> int:
        """Yrittää päätellä tähtimäärän JSON-datasta."""
        # Tarkista custom fieldit
        meta = item.get('meta', {})
        if isinstance(meta, dict):
            # Etsi mahdollisia rating-kenttiä
            for key in ['rating', 'stars', 'tahdet', 'arvosana']:
                if key in meta:
                    try:
                        rating = int(meta[key])
                        if 1 <= rating <= 5:
                            return rating
                    except:
                        pass
        
        # Jos ei löydy, palautetaan None
        return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Hae elokuvan nimi."""
        # Yritetään ensin h1-otsikkoa
        title_tag = soup.find('h1', class_='entry-title')
        if not title_tag:
            title_tag = soup.find('h1')
        
        if title_tag:
            return title_tag.get_text(strip=True)
        
        return "Tuntematon elokuva"
    
    def _extract_critic(self, soup: BeautifulSoup) -> str:
        """Hae kriitikon nimi."""
        # Yritetään ensin /kirjoittajat/-linkistä
        author_link = soup.find('a', href=lambda x: x and '/kirjoittajat/' in x)
        if author_link:
            name = author_link.get_text(strip=True)
            if name:
                return name
        
        # Yritetään author-metatagista
        author_tag = soup.find('meta', {'name': 'author'})
        if author_tag and author_tag.get('content'):
            content = author_tag['content'].strip()
            if content and content != "Episodi":
                return content
        
        # Yritetään by-author linkistä
        author_link = soup.find('a', class_='author')
        if author_link:
            name = author_link.get_text(strip=True)
            if name and name != "Episodi":
                return name
        
        return "Episodi"
    
    def _extract_rating(self, soup: BeautifulSoup) -> int:
        """Hae tähtimäärä."""
        # Etsi JSON-LD schema scriptistä
        import re
        
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                # Tarkista onko reviewRating
                if isinstance(data, dict) and 'reviewRating' in data:
                    rating_value = data['reviewRating'].get('ratingValue')
                    if rating_value:
                        rating = int(rating_value)
                        if 1 <= rating <= 5:
                            return rating
            except:
                continue
        
        # Varasuunnitelma: laske SVG-tähtikuvakkeet
        star_svgs = soup.find_all('svg', {'data-icon': 'star'})
        if star_svgs:
            star_count = len(star_svgs)
            if 1 <= star_count <= 5:
                return star_count
        
        # Etsi tähtisymboleita tekstistä
        rating_div = soup.find('div', class_='rating')
        if rating_div:
            stars_text = rating_div.get_text()
            star_count = stars_text.count('★') + stars_text.count('⭐')
            if 1 <= star_count <= 5:
                return star_count
        
        # Etsi tekstistä "4/5" tms.
        rating_pattern = r'(\d)/5'
        match = re.search(rating_pattern, soup.get_text())
        if match:
            rating = int(match.group(1))
            if 1 <= rating <= 5:
                return rating
        
        return None
    
    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Hae arvosteluteksti."""
        # Etsi artikkelin sisältö
        content_div = soup.find('div', class_='entry-content')
        if not content_div:
            content_div = soup.find('article')
        
        if content_div:
            # Poista skriptit ja tyylit
            for script in content_div(['script', 'style']):
                script.decompose()
            
            text = content_div.get_text(strip=True, separator=' ')
            return text[:500] if text else ""
        
        return ""
