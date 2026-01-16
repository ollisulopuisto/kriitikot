"""
Movie review scrapers for Finnish publications.

This package provides scrapers for:
- Helsingin Sanomat (HS.fi)
- Keskisuomalainen (KSML.fi)
- Iltalehti (IL.fi)
- Turun Sanomat (TS.fi)
- Suomen Kuvalehti (SK.fi)
- Ilta-Sanomat (IS.fi)
- Episodi (Episodi.fi)
- Muropaketti (Muropaketti.com)
- Film-O-Holic (Film-O-Holic.com)
- Kulttuuritoimitus (Kulttuuritoimitus.fi)

All scrapers return Review objects with standardized fields.
"""

from typing import Optional

# Import base classes
from .base import Review, BaseScraper

# Import all scrapers
from .hs import HSScraper
from .ksml import KSMLScraper
from .il import ILScraper
from .ts import TSScraper
from .sk import SKScraper
from .is_scraper import ISScraper
from .kaleva import KalevaScraper
from .episodi import EpisodiScraper
from .muropaketti import MuropakettiScraper
from .filmoholic import FilmOHolicScraper
from .kulttuuritoimitus import KulttuuritoimitusScraper
from .demokraatti import DemokraattiScraper
from .seura import SeuraScraper


# Scraper registry - maps source identifier to scraper instance
scrapers = {
    'hs': HSScraper(),
    'ksml': KSMLScraper(),
    'il': ILScraper(),
    'ts': TSScraper(),
    'sk': SKScraper(),
    'is': ISScraper(),
    'episodi': EpisodiScraper(),
    'muropaketti': MuropakettiScraper(),
    'filmoholic': FilmOHolicScraper(),
    'kulttuuritoimitus': KulttuuritoimitusScraper(),
    'demokraatti': DemokraattiScraper(),
    'seura': SeuraScraper(),
    'kaleva': KalevaScraper(),
}


def scrape_review(html_content: str, source: str = 'hs', source_url: Optional[str] = None) -> Optional[Review]:
    """
    Parse a review from HTML content using the appropriate scraper.
    
    Args:
        html_content: HTML content as string
        source: Source identifier ('hs', 'ksml', 'il', 'ts', 'sk', 'is', 'episodi', 'muropaketti', 'filmoholic', 'kulttuuritoimitus')
        source_url: Original URL (optional)
        
    Returns:
        Review object or None if parsing fails or source is unknown
        
    Raises:
        ValueError: If source is unknown
        
    Example:
        >>> html = '<html>...</html>'
        >>> review = scrape_review(html, source='hs', source_url='https://hs.fi/...')
        >>> print(review.movie_title)
    """
    scraper = scrapers.get(source)
    if not scraper:
        raise ValueError(f"Unknown source: {source}")
    
    return scraper.parse_html(html_content, source_url)


# Export all public symbols
__all__ = [
    # Base classes
    'Review',
    'BaseScraper',
    
    # Scraper classes
    'HSScraper',
    'KSMLScraper',
    'ILScraper',
    'TSScraper',
    'SKScraper',
    'ISScraper',
    'KalevaScraper',
    'EpisodiScraper',
    'MuropakettiScraper',
    'FilmOHolicScraper',
    'KulttuuritoimitusScraper',
    'DemokraattiScraper',
    'SeuraScraper',
    
    # Helper functions
    'scrape_review',
    'scrapers',
]
