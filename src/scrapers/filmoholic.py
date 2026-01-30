"""Film-O-Holic scraper for movie reviews."""
from .base import BaseScraper, Review
import re


class FilmOHolicScraper(BaseScraper):
    """Scraper for Film-O-Holic.com movie reviews.
    
    Film-O-Holic publishes movie reviews at:
    https://www.film-o-holic.com/arvostelut/
    
    Rating is in meta tag: <meta itemprop="rating" content="3" />
    """
    
    def __init__(self):
        super().__init__(publication_name="Film-O-Holic")
    
    def parse_html(self, html_content: str, source_url: str = None) -> Review:
        """Parse Film-O-Holic movie review.
        
        Args:
            html_content: HTML content as string
            source_url: Review URL (optional)
            
        Returns:
            Review object
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
    
    def _extract_title(self, soup):
        """Extract movie title from h1 tag.
        
        Title format: "Sisu 2 \n valkokangas"
        We need just the movie name before the category.
        """
        h1 = soup.find('h1')
        if h1:
            # Get text and split by whitespace/newlines
            text = h1.get_text()
            # Remove category tags like "valkokangas", "kotikatsomo"
            text = re.sub(r'\s*(valkokangas|kotikatsomo)\s*$', '', text, flags=re.IGNORECASE)
            return text.strip()
        
        return None
    
    def _extract_critic(self, soup):
        """Extract critic name from meta tag or byline.
        
        Critic is in: <meta name="author" content="Juha Rosenqvist" />
        Or in: <span itemprop="reviewer">Juha Rosenqvist</span>
        """
        # Try meta tag first
        author_meta = soup.find('meta', {'name': 'author'})
        if author_meta:
            return author_meta.get('content')
        
        # Try itemprop="reviewer"
        reviewer_span = soup.find('span', itemprop='reviewer')
        if reviewer_span:
            # Remove &nbsp; and clean
            return reviewer_span.get_text(strip=True).replace('\xa0', ' ')
        
        return None
    
    def _extract_rating(self, soup):
        """Extract star rating from meta tag.
        
        Rating is in: <meta itemprop="rating" content="3" />
        Returns integer 1-5 or None.
        """
        # Find meta tag with itemprop="rating"
        rating_meta = soup.find('meta', itemprop='rating')
        if rating_meta:
            try:
                rating = int(rating_meta.get('content', 0))
                if 1 <= rating <= 5:
                    return rating
            except (ValueError, TypeError):
                pass
        
        return None
    
    def _extract_text(self, soup):
        """Extract review text from paragraphs.
        
        Film-O-Holic reviews don't use <article> tag,
        but p-tags are directly in the main content.
        """
        # Find all p tags
        paragraphs = soup.find_all('p')
        text_parts = []
        
        for p in paragraphs:
            text = p.get_text(strip=True)
            
            # Skip short paragraphs
            if len(text) < 50:
                continue
            
            # Skip boilerplate text
            if any(skip in text.lower() for skip in [
                'lue myös', 'katso myös', 'jaa artikkeli',
                'tilaa uutiskirje', 'seuraa meitä', 'lukijakirje',
                'film-o-holic.com on', 'lisätietoa ja taustaa',
                'arvostelukaytannot', 'anna palautetta'
            ]):
                continue
            
            # Skip if it's in footer/header areas
            parent = p.parent
            if parent and parent.get('class'):
                parent_classes = ' '.join(parent.get('class', []))
                if any(skip in parent_classes.lower() for skip in ['footer', 'header', 'sidebar', 'meta']):
                    continue
            
            text_parts.append(text)
        
        return ' '.join(text_parts) if text_parts else None
