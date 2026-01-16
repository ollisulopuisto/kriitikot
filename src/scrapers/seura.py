"""
Seura.fi scraper
"""

from scrapers.base import BaseScraper, Review
from bs4 import BeautifulSoup
import re
from typing import Optional

class SeuraScraper(BaseScraper):
    """Scraper for Seura.fi movie reviews."""
    
    def __init__(self):
        super().__init__(publication_name="Seura")
    
    def parse_html(self, html_content: str, source_url: Optional[str] = None) -> Optional[Review]:
        """Parse HTML and return Review object."""
        soup = self.get_soup(html_content)

        # 1. Title
        title_tag = soup.find('h1', class_='wp-block-otavamedia-header__title')
        if not title_tag:
            return None
        movie_title = title_tag.get_text(strip=True)

        # 2. Critic
        critic_name = "Seura"  # Default
        author_meta = soup.find('meta', {'name': 'author'})
        if author_meta and author_meta.get('content'):
            critic_name = author_meta['content']
        else:
             # Fallback: JSON-LD
            import json
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    graph = data.get('@graph', [])
                    for item in graph:
                        if item.get('@type') == 'Article':
                             author = item.get('author', {})
                             if isinstance(author, dict) and 'name' in author:
                                 critic_name = author['name']
                                 break
                except:
                    continue

        # 3. Rating
        rating_stars = None
        # Try to parse from title: "viiden tähden elokuva"
        rating_map = {
            'yhden tähden': 1,
            'kahden tähden': 2,
            'kolmen tähden': 3,
            'neljän tähden': 4,
            'viiden tähden': 5
        }
        title_lower = movie_title.lower()
        for text, stars in rating_map.items():
            if text in title_lower:
                rating_stars = stars
                break
        
        # 4. Review Text
        review_text = ""
        # Main content usually in .entry-content or similar
        # Based on grep, content seems to be in standard wordpress blocks or similar, let's try generic
        # article body locators if specific class is tricky.
        # But from view_file we saw classes like `wp-block-otavamedia-header__excerpt` for summary.
        # Let's try to find the standard entry-content used in WordPress.
        content_div = soup.find('div', class_='entry-content')
        if not content_div:
             # Fallback
             content_div = soup.find('article')
        
        if content_div:
            # Remove scripts and styles
            for tag in content_div(['script', 'style']):
                tag.decompose()
            review_text = content_div.get_text(strip=True, separator=' ')

        return Review(
            movie_title=movie_title,
            critic_name=critic_name,
            rating_stars=rating_stars,
            review_text=review_text[:500] if review_text else "",
            source_url=source_url,
            source_publication=self.publication_name
        )
