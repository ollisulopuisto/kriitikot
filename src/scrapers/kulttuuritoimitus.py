"""Kulttuuritoimitus scraper for movie reviews."""
from scrapers.base import BaseScraper, Review
import requests
import json
from bs4 import BeautifulSoup


class KulttuuritoimitusScraper(BaseScraper):
    """Scraper for Kulttuuritoimitus.fi elokuvakritiikki using WordPress JSON API."""
    
    def __init__(self):
        super().__init__(publication_name="Kulttuuritoimitus")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def parse_html(self, html_content: str, source_url: str = None) -> Review:
        """
        Parse HTML and return Review object.
        
        Args:
            html_content: Raw HTML string
            source_url: URL for the review
            
        Returns:
            Review object with extracted data
        """
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
    
    def parse_json_api(self, json_data: dict, source_url: str = None) -> Review:
        """
        Parse review from WordPress JSON API response.
        
        Args:
            json_data: WordPress API JSON response for a single post
            source_url: URL for the review
            
        Returns:
            Review object with extracted data
        """
        # Extract title (WordPress stores it as HTML-rendered)
        title_obj = json_data.get('title', {})
        if isinstance(title_obj, dict):
            title = title_obj.get('rendered', '').strip()
        else:
            title = str(title_obj).strip()
        
        # Clean HTML tags from title
        title_soup = BeautifulSoup(title, 'html.parser')
        full_title = title_soup.get_text(strip=True)
        
        # Extract movie name from title
        # Kulttuuritoimitus pattern: "Some description – arviossa ensi-iltaelokuva MOVIENAME"
        # or "Some description – arviossa MOVIENAME"
        movie_title = self._extract_movie_name_from_title(full_title)
        
        # If pattern matching fails, try to get from Yoast keywords (first keyword is usually the movie)
        if not movie_title:
            yoast = json_data.get('yoast_head_json', {})
            keywords = yoast.get('keywords', [])
            if keywords and len(keywords) > 0:
                movie_title = keywords[0]
        
        # Fallback: use full title with common prefixes removed
        if not movie_title:
            prefixes = ['Arvio:', 'Arviossa', 'Kritiikki:', 'Elokuva-arvio:']
            movie_title = full_title
            for prefix in prefixes:
                if movie_title.startswith(prefix):
                    movie_title = movie_title[len(prefix):].strip()
                    break
        
        # Extract critic name from embedded author data
        critic_name = None
        embedded = json_data.get('_embedded', {})
        authors = embedded.get('author', [])
        if authors and len(authors) > 0:
            critic_name = authors[0].get('name')
        
        # If no embedded author, try yoast_head_json
        if not critic_name:
            yoast = json_data.get('yoast_head_json', {})
            critic_name = yoast.get('author')
        
        # Extract rating from content (look for star images or text)
        content_html = json_data.get('content', {})
        if isinstance(content_html, dict):
            content_html = content_html.get('rendered', '')
        
        soup = BeautifulSoup(content_html, 'html.parser')
        rating_stars = self._extract_rating(soup)
        
        # Extract review text from content
        review_text = self._extract_text(soup)
        
        # Use the link from JSON if no source_url provided
        if not source_url:
            source_url = json_data.get('link')
        
        return Review(
            movie_title=movie_title,
            critic_name=critic_name,
            rating_stars=rating_stars,
            review_text=review_text,
            source_url=source_url,
            source_publication=self.publication_name
        )
    
    def _extract_movie_name_from_title(self, title: str) -> str:
        """
        Extract movie name from Kulttuuritoimitus article title.
        
        Patterns:
        - "Description – arviossa ensi-iltaelokuva MOVIENAME"
        - "Description – arviossa MOVIENAME"
        - "Description arviossa MOVIENAME"
        """
        import re
        
        # Pattern 1: "arviossa ensi-iltaelokuva MOVIENAME"
        match = re.search(r'arviossa\s+ensi-iltaelokuva\s+(.+?)$', title, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Pattern 2: "arviossa MOVIENAME" (movie name is after "arviossa")
        match = re.search(r'arviossa\s+(.+?)$', title, re.IGNORECASE)
        if match:
            movie_name = match.group(1).strip()
            # Skip if it looks like continuation of description
            skip_words = ['miten', 'miksi', 'kuinka', 'mitä', 'onko', 'kuka']
            if not any(movie_name.lower().startswith(word) for word in skip_words):
                return movie_name
        
        # Pattern 3: Last part after dash if it looks like a movie name
        if '–' in title or '—' in title:
            parts = re.split(r'[–—]', title)
            if len(parts) > 1:
                last_part = parts[-1].strip()
                # Check if it starts with "arviossa"
                if last_part.lower().startswith('arviossa'):
                    # Extract movie name after "arviossa"
                    movie_match = re.search(r'arviossa\s+(.+)', last_part, re.IGNORECASE)
                    if movie_match:
                        return movie_match.group(1).strip()
        
        return None
    
    def _extract_title(self, soup):
        """
        Extract movie title from HTML.
        
        Kulttuuritoimitus has movie info in body text after rating stars:
        ARVOSTELU
        [star rating]
        <b>[Movie Title]</b>
        Ohjaus: [director]
        
        The structure is:
        <div class="et_pb_text_inner">
            <p><b>Movie Title</b></p>
            <ul>
                <li>Ohjaus: ...</li>
            </ul>
        </div>
        """
        import re
        
        # Method 1: Find <b> tag in the same et_pb_text_inner div that contains "Ohjaus:"
        # Look for list items with "Ohjaus:" or "Pääosissa:"
        for li in soup.find_all('li'):
            text = li.get_text(strip=True)
            if re.search(r'^(Ohjaus|Pääosissa|Käsikirjoitus)', text, re.IGNORECASE):
                # Found metadata list item - look for parent et_pb_text_inner div
                text_inner_div = li.find_parent('div', class_='et_pb_text_inner')
                if text_inner_div:
                    # Look for <b> or <strong> tags in this div
                    bold_tags = text_inner_div.find_all(['b', 'strong'])
                    for bold in bold_tags:
                        title = bold.get_text(strip=True)
                        # Skip if it's empty or contains metadata keywords
                        if title and len(title) > 1 and len(title) < 100:
                            skip_words = ['Ohjaus', 'Pääosissa', 'Ensi-ilta', 'Käsikirjoitus', 'Genre', 'ARVOSTELU']
                            if not any(word in title for word in skip_words):
                                return title
        
        # Method 2: Find movie title in body text after star rating
        # Look for pattern: stars → movie title → "Ohjaus:" or "Pääosissa:"
        
        # Find all paragraphs
        paragraphs = soup.find_all('p')
        
        for i, p in enumerate(paragraphs):
            text = p.get_text(strip=True)
            
            # Check if this paragraph contains "Ohjaus:" or "Pääosissa:"
            if re.search(r'^(Ohjaus|Pääosissa|Käsikirjoitus):', text, re.IGNORECASE):
                # Movie title should be in the previous paragraph(s)
                # Go backwards to find a short paragraph (likely the title)
                for j in range(i-1, max(i-4, -1), -1):
                    prev_text = paragraphs[j].get_text(strip=True)
                    
                    # Skip empty or very short
                    if len(prev_text) < 2:
                        continue
                    
                    # Skip if it contains "ARVOSTELU" or star symbols
                    if 'ARVOSTELU' in prev_text.upper() or '★' in prev_text or '⭐' in prev_text:
                        continue
                    
                    # Skip if it looks like metadata (contains "Ensi-ilta:" etc)
                    if re.search(r'(Ensi-ilta|Julkaistu|Genre):', prev_text, re.IGNORECASE):
                        continue
                    
                    # Skip very long paragraphs (likely review text, not title)
                    if len(prev_text) > 100:
                        continue
                    
                    # This is likely the movie title
                    return prev_text
        
        # Method 2: Fallback to headline parsing
        title = None
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
        else:
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content', '').strip()
                title = title.split(' - Kulttuuritoimitus')[0].strip()
        
        if title:
            # Try to extract movie name from title pattern
            movie_name = self._extract_movie_name_from_title(title)
            if movie_name:
                return movie_name
            
            # Fallback: remove common prefixes
            prefixes = ['Arvio:', 'Arviossa', 'Kritiikki:', 'Elokuva-arvio:']
            for prefix in prefixes:
                if title.startswith(prefix):
                    return title[len(prefix):].strip()
            
            return title
        
        return None
    
    def _extract_critic(self, soup):
        """Extract critic name from HTML."""
        # Try meta author
        author_meta = soup.find('meta', {'name': 'author'})
        if author_meta:
            return author_meta.get('content')
        
        # Try yoast JSON-LD
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            if script.string:
                try:
                    data = json.loads(script.string)
                    if '@graph' in data:
                        for item in data['@graph']:
                            if item.get('@type') == 'Article':
                                author = item.get('author', {})
                                if isinstance(author, dict):
                                    name = author.get('name')
                                    if name:
                                        return name
                except:
                    pass
        
        # Try author link
        author_link = soup.find('a', rel='author')
        if author_link:
            return author_link.get_text(strip=True)
        
        return None
    
    def _extract_rating(self, soup):
        """Extract star rating (1-5) from HTML."""
        # Kulttuuritoimitus uses usr plugin with image.php for stars
        # Look for: <img class="usr" src="...image.php?...&rat=4&..." />
        
        usr_img = soup.find('img', class_='usr')
        if usr_img:
            src = usr_img.get('src', '')
            # Extract rat parameter from URL
            if 'rat=' in src:
                try:
                    rat_part = src.split('rat=')[1]
                    rating_str = rat_part.split('&')[0]
                    rating = int(float(rating_str))
                    if 1 <= rating <= 5:
                        return rating
                except:
                    pass
        
        # Alternative: count star symbols
        text = soup.get_text()
        stars = text.count('★') + text.count('⭐')
        if 1 <= stars <= 5:
            return stars
        
        return None
    
    def _extract_text(self, soup):
        """Extract review text from HTML."""
        # Remove script and style elements
        for script in soup(['script', 'style']):
            script.decompose()
        
        # Find all paragraphs
        paragraphs = soup.find_all('p')
        
        text_parts = []
        
        for p in paragraphs:
            text = p.get_text(strip=True)
            
            # Skip short paragraphs
            if len(text) < 30:
                continue
            
            # Skip boilerplate
            skip_phrases = [
                'kuva:',
                'myös nämä saattavat kiinnostaa',
                'arvostelu',
                'kuuntele:',
                'katso:',
                'lue lisää',
                'kirjoittanut',
                'arvioitu lukuaika',
                '[et_pb',  # WordPress shortcodes
                'admin_label',
                '_builder_version'
            ]
            
            if any(phrase in text.lower() for phrase in skip_phrases):
                continue
            
            # Skip if text is mostly WordPress shortcode syntax
            if text.startswith('[') or '="' in text[:50]:
                continue
            
            text_parts.append(text)
        
        return ' '.join(text_parts) if text_parts else None
