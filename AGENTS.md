# AI Agent Instructions for Kriitikot Development

This document provides step-by-step instructions for AI coding agents (like Claude) on how to extend the Kriitikot movie review aggregator with new scrapers and functionality.

## Project Overview

**Kriitikot** is a Finnish movie review aggregator that:
- Scrapes movie reviews from multiple Finnish media sources
- Stores reviews in a SQLite database with fuzzy movie title matching
- Provides a Flask web interface for browsing reviews
- Supports automated batch updates via discovery system

**Current Architecture:**
- **Language**: Python 3.9+
- **Web Framework**: Flask
- **Database**: SQLite + SQLAlchemy ORM
- **Scraping**: BeautifulSoup4, requests
- **Testing**: pytest

**Active Sources (8):**
- Helsingin Sanomat (HS)
- Keskisuomalainen (KSML)
- Iltalehti (IL)
- Turun Sanomat (TS)
- Suomen Kuvalehti (SK)
- Ilta-Sanomat (IS)
- Episodi
- Muropaketti

## How to Add a New Scraper

### Step 1: Create the Scraper Module

Create a new file in `src/scrapers/` named after the publication (e.g., `filmoholic.py`):

```python
"""Film-O-Holic scraper for movie reviews."""
from scrapers.base import BaseScraper, Review
import re


class FilmOHolicScraper(BaseScraper):
    """Scraper for Film-O-Holic.com movie reviews."""
    
    def __init__(self):
        super().__init__(publication_name="Film-O-Holic")
    
    def parse_html(self, html_content: str, source_url: str = None) -> Review:
        """Parse HTML and return Review object.
        
        Args:
            html_content: Raw HTML string
            source_url: Optional URL for the review
            
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
    
    def _extract_title(self, soup):
        """Extract movie title from HTML."""
        # Implementation here
        pass
    
    def _extract_critic(self, soup):
        """Extract critic name from HTML."""
        # Implementation here
        pass
    
    def _extract_rating(self, soup):
        """Extract star rating (1-5 integer or None)."""
        # Implementation here
        pass
    
    def _extract_text(self, soup):
        """Extract review text."""
        # Implementation here
        pass
```

**Key Points:**
- Inherit from `BaseScraper`
- Call `super().__init__(publication_name="YourPublication")`
- Implement `parse_html()` method
- Return `Review` object with all fields
- Use `self.get_soup(html_content)` for BeautifulSoup parsing
- Rating must be integer 1-5 or None

### Step 2: Register the Scraper

Edit `src/scrapers/__init__.py`:

```python
# 1. Update docstring
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
- Film-O-Holic (Film-O-Holic.com)  # ADD THIS

All scrapers return Review objects with standardized fields.
"""

# 2. Import the scraper
from .filmoholic import FilmOHolicScraper

# 3. Add to scrapers registry
scrapers = {
    'hs': HSScraper(),
    'ksml': KSMLScraper(),
    'il': ILScraper(),
    'ts': TSScraper(),
    'sk': SKScraper(),
    'is': ISScraper(),
    'episodi': EpisodiScraper(),
    'muropaketti': MuropakettiScraper(),
    'filmoholic': FilmOHolicScraper(),  # ADD THIS
}

# 4. Update docstring in scrape_review()
# Update source parameter: ('hs', 'ksml', 'il', 'ts', 'sk', 'is', 'episodi', 'muropaketti', 'filmoholic')

# 5. Add to __all__ exports
__all__ = [
    # ... existing exports ...
    'FilmOHolicScraper',  # ADD THIS
]
```

### Step 3: Add Discovery Support

Edit `src/discovery.py`:

```python
# 1. Add to CATEGORY_PAGES
CATEGORY_PAGES = {
    'sk': 'https://suomenkuvalehti.fi/avainsana/elokuva/',
    'hs': 'https://www.hs.fi/aihe/elokuvat/',
    # ... other sources ...
    'filmoholic': 'https://film-o-holic.com/reviews/',  # ADD THIS
}

# 2. Update docstring in find_review_links()
# Args: source: Lähteen tunniste ('sk', 'hs', 'ts', 'il', 'ksml', 'is', 'episodi', 'muropaketti', 'filmoholic')

# 3. Add to conditional logic in find_review_links()
elif source == 'filmoholic':
    html = self._fetch_url(url)
    soup = BeautifulSoup(html, 'html.parser')
    return self._find_filmoholic_reviews(soup, limit)

# 4. Implement discovery method
def _find_filmoholic_reviews(self, soup: BeautifulSoup, limit: int) -> List[Dict[str, str]]:
    """
    Find Film-O-Holic reviews from category page.
    
    Returns list of {'title': '...', 'url': '...'} dicts.
    """
    reviews = []
    
    # Example: Find all links with specific class/pattern
    for link in soup.find_all('a', class_='review-link'):
        title = link.get_text(strip=True)
        url = link['href']
        
        # Make absolute URL if needed
        if url.startswith('/'):
            url = 'https://film-o-holic.com' + url
        
        reviews.append({
            'title': title,
            'url': url
        })
        
        if len(reviews) >= limit:
            break
    
    return reviews

# 5. Update discover_new_reviews() docstring
# Args: source: Lähteen tunniste ('sk', 'hs', 'ts', 'il', 'ksml', 'is', 'episodi', 'muropaketti', 'filmoholic')

# 6. Update main section test sources
for source in ['hs', 'ts', 'il', 'ksml', 'sk', 'is', 'episodi', 'muropaketti', 'filmoholic']:
```

### Step 4: Add to Discovery Importer

Edit `src/discovery_importer.py`:

```python
# 1. Import the scraper
from scrapers.filmoholic import FilmOHolicScraper

# 2. Add to scrapers dict in __init__
self.scrapers = {
    'hs': HSScraper(),
    'ksml': KSMLScraper(),
    'il': ILScraper(),
    'ts': TSScraper(),
    'sk': SKScraper(),
    'is': ISScraper(),
    'episodi': EpisodiScraper(),
    'muropaketti': MuropakettiScraper(),
    'filmoholic': FilmOHolicScraper(),  # ADD THIS
}
```

### Step 5: Add Publication to Database

Run this once to add the new publication:

```python
from models import get_session, Publication

session = get_session()

# Check if already exists
existing = session.query(Publication).filter_by(name='Film-O-Holic').first()

if not existing:
    filmoholic = Publication(name='Film-O-Holic', short_name='filmoholic')
    session.add(filmoholic)
    session.commit()
    print("✅ Film-O-Holic added to database")

session.close()
```

### Step 6: Test the Scraper

Create test file `tests/test_data/filmoholic_review_1.html` with sample HTML, then:

```python
# Test in tests/test_scraper.py
def test_filmoholic_scraper_basic():
    """Test Film-O-Holic scraper with basic review."""
    scraper = FilmOHolicScraper()
    
    with open('tests/test_data/filmoholic_review_1.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    review = scraper.parse_html(html, source_url='https://film-o-holic.com/review/test')
    
    assert review is not None
    assert review.movie_title == "Expected Movie Title"
    assert review.rating_stars == 4
    assert review.critic_name == "Expected Critic"
    assert "Expected text snippet" in review.review_text
```

Run tests:
```bash
pytest tests/test_scraper.py::test_filmoholic_scraper_basic -v
```

### Step 7: Import Reviews

Test the full pipeline:

```python
from discovery_importer import DiscoveryImporter

importer = DiscoveryImporter()
importer.import_discovered_reviews('filmoholic', limit=5)
```

## Common Scraping Patterns

### Extract Title

```python
def _extract_title(self, soup):
    """Common patterns for extracting movie title."""
    
    # Pattern 1: From h1 tag
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text(strip=True)
        # Remove prefix like "Review: " or "Arvio: "
        title = re.sub(r'^(Review|Arvio)[:\s]+', '', title, flags=re.IGNORECASE)
        return title
    
    # Pattern 2: From meta tag
    og_title = soup.find('meta', property='og:title')
    if og_title:
        return og_title.get('content')
    
    # Pattern 3: From specific div/class
    title_div = soup.find('div', class_='movie-title')
    if title_div:
        return title_div.get_text(strip=True)
    
    # Pattern 4: From text before specific marker
    for p in soup.find_all('p'):
        text = p.get_text()
        if 'Release date:' in text or 'Ensi-ilta:' in text:
            # Title is before the marker
            parts = text.split('Release date:', 1)
            return parts[0].strip()
    
    return None
```

### Extract Critic Name

```python
def _extract_critic(self, soup):
    """Common patterns for extracting critic name."""
    
    # Pattern 1: Meta tag
    author_meta = soup.find('meta', {'name': 'author'})
    if author_meta:
        return author_meta.get('content')
    
    # Pattern 2: Specific class
    author_div = soup.find('div', class_='author-name')
    if author_div:
        return author_div.get_text(strip=True)
    
    # Pattern 3: rel="author" link
    author_link = soup.find('a', rel='author')
    if author_link:
        return author_link.get_text(strip=True)
    
    # Pattern 4: JSON-LD schema
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
                                return author.get('name')
            except:
                pass
    
    return None
```

### Extract Star Rating

```python
def _extract_rating(self, soup):
    """Common patterns for extracting star rating (1-5)."""
    
    # Pattern 1: Count star symbols (★, ⭐)
    rating_div = soup.find('div', class_='rating')
    if rating_div:
        text = rating_div.get_text()
        stars = text.count('★') + text.count('⭐')
        if 1 <= stars <= 5:
            return stars
    
    # Pattern 2: Parse "X/5" text
    for elem in soup.find_all(['div', 'span', 'p']):
        text = elem.get_text()
        match = re.search(r'(\d+)/5', text)
        if match:
            rating = int(match.group(1))
            if 1 <= rating <= 5:
                return rating
    
    # Pattern 3: Image alt text
    for img in soup.find_all('img'):
        alt = img.get('alt', '')
        if 'rating' in alt.lower() or 'stars' in alt.lower():
            match = re.search(r'(\d+)', alt)
            if match:
                rating = int(match.group(1))
                if 1 <= rating <= 5:
                    return rating
    
    # Pattern 4: Image filename (like Muropaketti)
    for img in soup.find_all('img'):
        for attr in ['src', 'data-src']:
            src = img.get(attr, '')
            if 'star' in src or 'rating' in src:
                # Extract number from filename
                match = re.search(r'(\d+)', src.split('/')[-1])
                if match:
                    rating = int(match.group(1))
                    if 1 <= rating <= 5:
                        return rating
    
    # Pattern 5: Finnish text ("neljä tähteä" = 4 stars)
    finnish_numbers = {
        'yksi': 1, 'yhden': 1,
        'kaksi': 2, 'kahden': 2,
        'kolme': 3, 'kolmen': 3,
        'neljä': 4, 'neljän': 4,
        'viisi': 5, 'viiden': 5
    }
    
    text = soup.get_text().lower()
    for word, num in finnish_numbers.items():
        if f'{word} tähte' in text:
            return num
    
    # Pattern 6: JSON-LD schema.org Review
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        if script.string:
            try:
                data = json.loads(script.string)
                if data.get('@type') == 'Review':
                    rating_value = data.get('reviewRating', {}).get('ratingValue')
                    if rating_value:
                        rating = int(float(rating_value))
                        if 1 <= rating <= 5:
                            return rating
            except:
                pass
    
    return None
```

### Extract Review Text

```python
def _extract_text(self, soup):
    """Extract review text from paragraphs."""
    
    # Find main content area
    content_div = (
        soup.find('div', class_='entry-content') or
        soup.find('article') or
        soup.find('div', class_='content') or
        soup
    )
    
    paragraphs = content_div.find_all('p')
    text_parts = []
    
    for p in paragraphs:
        text = p.get_text(strip=True)
        
        # Skip short paragraphs
        if len(text) < 30:
            continue
        
        # Skip common boilerplate
        if any(skip in text.lower() for skip in [
            'read also', 'lue myös', 'katso myös',
            'share this', 'jaa artikkeli', 'tilaa uutiskirje'
        ]):
            continue
        
        text_parts.append(text)
    
    return ' '.join(text_parts) if text_parts else None
```

## Special Cases & Tips

### WordPress JSON API (like Episodi)

For sites using WordPress, check for `/wp-json/wp/v2/` API:

```python
def parse_json_api(self, json_data: dict, source_url: str = None) -> Review:
    """Parse review from WordPress JSON API response."""
    
    title = json_data.get('title', {}).get('rendered', '').strip()
    
    # Get embedded author data
    embedded = json_data.get('_embedded', {})
    authors = embedded.get('author', [])
    critic_name = authors[0].get('name') if authors else None
    
    # Extract rating from JSON-LD in content
    content_html = json_data.get('content', {}).get('rendered', '')
    soup = BeautifulSoup(content_html, 'html.parser')
    rating = self._extract_rating_from_jsonld(soup)
    
    return Review(...)
```

### Handling UTF-8 Encoding Issues (like IL)

Some sites have double-encoded UTF-8:

```python
# Double-encoded star: ⭐ appears as â\xad\x90
text = element.get_text()
stars = text.count('â\xad\x90')  # Count double-encoded stars
if stars > 0:
    return stars
```

### Normalizing Titles

Uppercase titles should be normalized:

```python
title = parts[0].strip()
# If entire title is uppercase (e.g., "SISU 2"), convert to title case
if title.isupper() and len(title.split()) <= 4:
    title = title.title()
```

### Discovery with JSON APIs

Some sites provide JSON data:

```python
def _find_source_reviews_json(self, api_url: str, limit: int) -> List[Dict[str, str]]:
    """Fetch reviews from JSON API."""
    reviews = []
    
    try:
        response = requests.get(
            api_url,
            params={'per_page': limit, 'orderby': 'date'},
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        for item in data:
            reviews.append({
                'title': item.get('title', ''),
                'url': item.get('link', '')
            })
    except Exception as e:
        print(f"JSON API error: {e}")
    
    return reviews
```

## Testing Checklist

Before committing a new scraper:

- [ ] Scraper inherits from `BaseScraper`
- [ ] All 4 extract methods implemented (`_extract_title`, `_extract_critic`, `_extract_rating`, `_extract_text`)
- [ ] Registered in `scrapers/__init__.py`
- [ ] Added to `discovery.py` with discovery method
- [ ] Added to `discovery_importer.py`
- [ ] Publication added to database
- [ ] Test HTML saved in `tests/test_data/`
- [ ] Test case written in `tests/test_scraper.py`
- [ ] Tests pass: `pytest tests/test_scraper.py -v`
- [ ] Successfully imports at least 1 review to database
- [ ] Verified in `db_status.py` output

## Database Schema

Reviews are stored with these relationships:

```
Movie (fuzzy matched, threshold 0.9)
  ├─ title (canonical)
  └─ reviews[]

Critic
  ├─ name
  └─ reviews[]

Publication
  ├─ name (full name)
  ├─ short_name (lowercase identifier)
  └─ reviews[]

Review
  ├─ movie_id (FK)
  ├─ critic_id (FK)
  ├─ publication_id (FK)
  ├─ rating_stars (1-5 or NULL)
  ├─ review_text (TEXT)
  └─ source_url (UNIQUE - prevents duplicates)
```

## Batch Import Scripts

After adding a scraper, it will work with existing batch scripts:

```bash
# Import from specific source
cd src && python3 -c "from discovery_importer import DiscoveryImporter; DiscoveryImporter().import_discovered_reviews('filmoholic', limit=10)"

# Run full batch update (all sources)
cd src && python3 batch_update.py
```

## File Structure Reference

```
kriitikot/
├── src/
│   ├── scrapers/
│   │   ├── __init__.py       # Registry - ADD HERE
│   │   ├── base.py           # BaseScraper & Review classes
│   │   ├── hs.py             # Example scraper
│   │   └── newsource.py      # NEW SCRAPER HERE
│   ├── discovery.py          # Discovery system - ADD HERE
│   ├── discovery_importer.py # Importer - ADD HERE
│   ├── models.py             # Database models
│   ├── app.py                # Flask web app
│   └── batch_update.py       # Automated updates
├── tests/
│   ├── test_scraper.py       # Tests - ADD HERE
│   └── test_data/
│       └── newsource_*.html  # Test HTML - ADD HERE
└── docs/
    └── README.md             # Update when adding scraper
```

## Common Issues & Solutions

### Issue: "Publication not found in database"
**Solution**: Run the database add script from Step 5.

### Issue: "Rating is None for all reviews"
**Solution**: Check rating extraction logic. Use browser DevTools to inspect the actual HTML structure of star ratings.

### Issue: "Title includes article headline instead of movie name"
**Solution**: Look for structured data (JSON-LD, meta tags, or specific divs) rather than h1 tag. Movie name is often in a separate element from the article headline.

### Issue: "Duplicate reviews imported"
**Solution**: Reviews are deduplicated by `source_url`. Ensure the scraper receives the canonical URL (not URL with query parameters that change).

### Issue: "Finnish characters (ä, ö) display incorrectly"
**Solution**: Always use `encoding='utf-8'` when reading/writing files. Check for double-encoding issues.

### Issue: "Discovery finds wrong articles"
**Solution**: Tighten discovery regex patterns. Add validation (e.g., URL must contain '/review/' or title must start with specific keyword).

## Additional Resources

- **SQLAlchemy ORM**: `models.py` contains all database models
- **Movie Normalizer**: `movie_normalizer.py` handles fuzzy title matching
- **Flask Routes**: `app.py` shows web interface structure
- **Existing Scrapers**: Study `scrapers/hs.py`, `scrapers/episodi.py`, `scrapers/muropaketti.py` for examples

## Questions?

Check existing scrapers for examples:
- **Simple HTML**: `src/scrapers/hs.py`
- **JSON API**: `src/scrapers/episodi.py`
- **Complex rating extraction**: `src/scrapers/muropaketti.py`
- **UTF-8 encoding issues**: `src/scrapers/il.py`

All scrapers follow the same pattern - study them and adapt to your target site's structure.

Don't use ! exclamation marks in your prompts, because I use zsh and it can break zsh.