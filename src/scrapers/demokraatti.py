
import json
import re
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from .base import Review, BaseScraper

class DemokraattiScraper(BaseScraper):
    """Demokraatti.fi movie review scraper."""
    
    def __init__(self):
        super().__init__("Demokraatti")
    
    def parse_html(self, html_content: str, source_url: Optional[str] = None) -> Optional[Review]:
        """
        Parses Demokraatti.fi HTML content and returns a Review object.
        Data is extracted from __NEXT_DATA__ JSON.
        """
        soup = self.get_soup(html_content)
        
        # 1. Extract JSON data
        next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
        if not next_data_script:
            return None
            
        try:
            data = json.loads(next_data_script.string)
        except json.JSONDecodeError:
            return None
            
        # 2. Navigate to post data
        # Path: props.pageProps.dehydratedState.queries -> singlePostMain -> state.data.singlePost
        post_data = self._extract_post_data(data)
        if not post_data:
            return None
            
        # 3. Check if it's a movie review
        if not self._is_movie_review(post_data):
            return None
            
        # 4. Extract fields
        movie_title = self._extract_title(post_data)
        critic_name = self._extract_author(post_data)
        review_text = self._extract_review_text(post_data)
        rating = self._extract_rating(post_data, review_text)
        
        # URL
        url = source_url or post_data.get('link') or post_data.get('slug')
        if url and not url.startswith('http'):
            # If slug, construct full URL (though usually link is full)
            if 'demokraatti.fi' not in url:
                url = f"https://demokraatti.fi/{url}"

        return Review(
            movie_title=movie_title,
            critic_name=critic_name,
            rating_stars=rating,
            review_text=review_text,
            source_url=url,
            source_publication=self.publication_name,
            raw_data=post_data
        )

    def _extract_post_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Navigate through Next.js data to find the single post."""
        try:
            queries = data['props']['pageProps']['dehydratedState']['queries']
            for query in queries:
                key = query.get('queryKey', [])
                # Key is like ['singlePostMain', 'slug-string']
                if isinstance(key, list) and len(key) > 0 and key[0] == 'singlePostMain':
                    return query['state']['data']['singlePost']
        except (KeyError, TypeError, IndexError):
            pass
        return None

    def _is_movie_review(self, data: Dict[str, Any]) -> bool:
        """Check if the post is a movie review."""
        # 1. Check title for "Arvio:"
        title = data.get('title', '')
        if 'Arvio:' in title or 'arvio:' in title:
            return True
            
        # 2. Check categories
        categories = data.get('categories', {}).get('nodes', [])
        for cat in categories:
            name = cat.get('name', '').lower()
            if 'elokuva' in name:
                return True
                
        return False

    def _extract_title(self, data: Dict[str, Any]) -> str:
        """
        Extract movie title.
        Prioritizes extraction from the 'well' infobox in the content.
        Fallbacks to the main post title.
        """
        # 1. Try to extract from content infobox (div.well)
        content_html = data.get('content', '')
        if content_html:
            soup = BeautifulSoup(content_html, 'html.parser')
            well = soup.find('div', class_='well')
            if well:
                # Look for 'ELOKUVA' strong tag
                elokuva_tag = well.find('strong', string=re.compile(r'ELOKUVA', re.IGNORECASE))
                if elokuva_tag:
                    # The title is usually in the next 'em' tag
                    # It might be separated by br, whitespace etc.
                    # Let's look for the first 'em' tag in the well which is likely the title
                    # akin to the structure: <strong>ELOKUVA</strong>:<br/><em>Title</em>
                    title_em = well.find('em')
                    if title_em:
                         return title_em.get_text().strip()
        
        # 2. Fallback to main title
        title = data.get('title', '')
        # Remove "Arvio: " prefix if present
        cleaned = re.sub(r'^Arvio:\s*', '', title, flags=re.IGNORECASE)
        
        return cleaned.strip()

    def _extract_author(self, data: Dict[str, Any]) -> str:
        """Extract author name."""
        try:
            return data['author']['node']['name']
        except (KeyError, TypeError):
            return "Unknown"

    def _extract_review_text(self, data: Dict[str, Any]) -> str:
        """Extract and clean review text."""
        # Content is HTML string
        content_html = data.get('content', '')
        if not content_html:
            return ""
            
        # Parse HTML to text
        soup = BeautifulSoup(content_html, 'html.parser')
        
        # Remove unwanted elements? (scripts, etc)
        # For simple text extraction:
        return soup.get_text(separator='\n\n').strip()

    def _extract_rating(self, data: Dict[str, Any], review_text: str) -> Optional[int]:
        """Extract star rating from content."""
        # Search for star characters in content
        # Check raw html content first as text conversion might parse stars differently? 
        # Actually BS4 handles unicode stars fine.
        
        # Look for ★ (U+2605)
        # Often formatted as sequence of stars.
        
        content = data.get('content', '')
        
        # Count filled stars
        stars = content.count('★')
        
        # Sanity check: verify it looks like a rating (usually accompanied by empty stars ☆ or total 5 chars)
        # But if we just find stars, it's likely a rating.
        # However, check max 5.
        if stars > 0:
            return min(stars, 5)
            
        return None
