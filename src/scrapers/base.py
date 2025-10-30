"""
Base classes for movie review scrapers.

Provides common data structures and abstract base class for all scrapers.
"""

from typing import Optional, Dict, Any


class Review:
    """Yhtenäinen tietorakenne arvostelulle, riippumaton lähteestä."""
    
    def __init__(
        self,
        movie_title: str,
        critic_name: str,
        rating_stars: Optional[int] = None,
        review_text: Optional[str] = None,
        source_url: Optional[str] = None,
        source_publication: str = "Unknown",
        raw_data: Optional[Dict[str, Any]] = None
    ):
        self.movie_title = movie_title
        self.critic_name = critic_name
        self.rating_stars = rating_stars  # 1-5 tähteä tai None
        self.review_text = review_text
        self.source_url = source_url
        self.source_publication = source_publication
        self.raw_data = raw_data or {}
    
    def to_dict(self) -> dict:
        """Palauttaa arvostelun sanakirjana."""
        return {
            'movie_title': self.movie_title,
            'critic_name': self.critic_name,
            'rating_stars': self.rating_stars,
            'review_text': self.review_text,
            'source_url': self.source_url,
            'source_publication': self.source_publication
        }


class BaseScraper:
    """Abstract base class for all scrapers."""
    
    def __init__(self, publication_name: str):
        self.publication_name = publication_name
    
    def parse_html(self, html_content: str, source_url: Optional[str] = None) -> Optional[Review]:
        """
        Parse HTML content and return a Review object.
        
        Args:
            html_content: HTML content as string
            source_url: Original URL (optional)
            
        Returns:
            Review object or None if parsing fails
        """
        raise NotImplementedError("Subclasses must implement parse_html()")
    
    def parse_file(self, filepath: str) -> Optional[Review]:
        """
        Parse HTML from file and return a Review object.
        
        Args:
            filepath: Path to HTML file
            
        Returns:
            Review object or None if parsing fails
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return self.parse_html(html_content)
        except Exception as e:
            print(f"Error reading file {filepath}: {e}")
            return None
