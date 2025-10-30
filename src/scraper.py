"""
Deprecated: This module is kept for backward compatibility.
Please use 'from scrapers import ...' instead.

All scraper classes have been moved to the scrapers/ package:
- Review, BaseScraper -> scrapers.base
- HSScraper -> scrapers.hs
- KSMLScraper -> scrapers.ksml
- ILScraper -> scrapers.il
- TSScraper -> scrapers.ts
- SKScraper -> scrapers.sk
- ISScraper -> scrapers.is_scraper
"""

import warnings

# Re-export everything from the new scrapers package for backward compatibility
from scrapers import (
    Review,
    BaseScraper,
    HSScraper,
    KSMLScraper,
    ILScraper,
    TSScraper,
    SKScraper,
    ISScraper,
    scrape_review,
    scrapers,
)

# Warn users about deprecation (only once)
warnings.warn(
    "Importing from 'scraper' is deprecated. Please use 'from scrapers import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    'Review',
    'BaseScraper',
    'HSScraper',
    'KSMLScraper',
    'ILScraper',
    'TSScraper',
    'SKScraper',
    'ISScraper',
    'scrape_review',
    'scrapers',
]
