# GitHub Copilot Instructions for Kriitikot

## Project Overview

Kriitikot is a Finnish movie review aggregator web application that collects, analyzes, and displays movie reviews from various Finnish media sources. The application scrapes reviews from multiple Finnish publications and stores them in a SQLite database with a Flask-based web interface.

## Core Architecture

### Technology Stack
- **Language**: Python 3.9+
- **Web Framework**: Flask
- **Database**: SQLite with SQLAlchemy ORM
- **Scraping**: BeautifulSoup4, requests
- **Testing**: pytest

### Project Structure
```
kriitikot/
├── src/
│   ├── scrapers/          # Modular web scrapers (one per source)
│   │   ├── base.py        # Review class + BaseScraper
│   │   ├── hs.py          # Helsingin Sanomat
│   │   ├── ksml.py        # Keskisuomalainen
│   │   ├── il.py          # Iltalehti
│   │   ├── ts.py          # Turun Sanomat
│   │   ├── sk.py          # Suomen Kuvalehti
│   │   └── is_scraper.py  # Ilta-Sanomat
│   ├── app.py             # Flask web application
│   ├── models.py          # SQLAlchemy database models
│   ├── discovery.py       # Automatic review discovery
│   ├── movie_normalizer.py # Movie title normalization
│   └── batch_update.py    # Automated batch updates
├── templates/             # Flask HTML templates
├── static/                # CSS/JS assets
├── tests/                 # pytest test suite
│   ├── test_scraper.py   # Scraper tests
│   └── test_data/        # Test HTML fixtures
└── docs/                  # Extensive documentation
```

## Database Schema

The application uses SQLAlchemy ORM with four main models:
- **Movies**: Stores normalized movie titles (fuzzy matching with 0.9 threshold)
- **Critics**: Movie critics from various publications
- **Publications**: Media sources (HS, KSML, IL, TS, SK, IS)
- **Reviews**: Complete review data with relationships to Movies, Critics, and Publications

URL-based duplicate prevention is implemented to avoid duplicate reviews.

## Coding Standards

### Python Style
- Follow PEP 8 conventions
- Use meaningful variable names in English (code) and Finnish (comments/docs when appropriate)
- Type hints are not currently used but can be added for new code
- Keep functions focused and modular

### Scraper Development
Each scraper in `src/scrapers/` follows this pattern:

```python
from scrapers.base import BaseScraper, Review

class ExampleScraper(BaseScraper):
    """Scraper for Example Publication."""
    
    def parse_html(self, html_content: str, source_url: str = None) -> Review:
        """Parse HTML and return Review object.
        
        Args:
            html_content: Raw HTML string
            source_url: Optional URL for the review
            
        Returns:
            Review object with extracted data
        """
        soup = self.get_soup(html_content)
        
        # Extract data using BeautifulSoup
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
```

### Review Object
The `Review` class (in `scrapers/base.py`) is the universal data structure:
- `movie_title`: String, movie name
- `critic_name`: String, critic's name
- `rating_stars`: Integer 1-5 or None
- `review_text`: String, review content
- `source_url`: String, source URL
- `source_publication`: String, publication name

### Rating Extraction
Star ratings (1-5) can be extracted from:
- Unicode star symbols (★, ⭐)
- Finnish text ("neljä tähteä" = 4 stars)
- Numeric values (4/5, 4 tähteä)
- Image alt text or aria-labels

## Testing Guidelines

### Test Structure
- All scraper tests are in `tests/test_scraper.py`
- Test data (HTML fixtures) stored in `tests/test_data/`
- Use pytest for all tests
- Current test count: 13 tests (100% passing)

### Running Tests
```bash
# All tests
pytest

# Verbose mode
pytest -v -s

# Specific test
pytest tests/test_scraper.py::test_hs_scraper_basic -v
```

### Writing Tests
When adding a new scraper, create corresponding tests:

```python
def test_example_scraper_basic():
    """Test Example scraper with basic review."""
    scraper = ExampleScraper()
    with open('tests/test_data/example_basic.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    review = scraper.parse_html(html, source_url='https://example.fi/review')
    
    assert review is not None
    assert review.movie_title == "Expected Movie Title"
    assert review.rating_stars == 4
    assert review.critic_name == "Expected Critic"
    assert "Expected text snippet" in review.review_text
```

## Development Workflow

### Adding a New Scraper
1. Create new file in `src/scrapers/` (e.g., `example.py`)
2. Inherit from `BaseScraper` and implement `parse_html()`
3. Add to `scrapers/__init__.py` registry
4. Create test HTML fixtures in `tests/test_data/`
5. Write pytest tests in `tests/test_scraper.py`
6. Update documentation in `docs/` if needed

### Discovery System
The discovery system (`src/discovery.py`) automatically finds new reviews:
- Each source has a specific discovery strategy
- Returns metadata (title, URL, date)
- Can be integrated with scrapers for automatic import

### Batch Updates
The `batch_update.py` script automates review collection:
- Runs discovery for all sources
- Scrapes and stores reviews in database
- Prevents duplicates via URL checking
- Can be scheduled with cron/systemd

## Common Patterns

### HTML Parsing with BeautifulSoup
```python
soup = self.get_soup(html_content)

# CSS selectors
title = soup.select_one('h1.title')

# Find by attributes
rating = soup.find('span', {'class': 'rating'})

# Text extraction with fallbacks
text = title.get_text(strip=True) if title else None
```

### Error Handling
- Scrapers should return None or raise exceptions on parse failures
- Use try/except for fragile operations
- Log warnings for missing optional data

### Database Operations
```python
from models import Movie, Review, Critic, Publication
from sqlalchemy.orm import Session

# Create session
with Session(engine) as session:
    # Fuzzy match movies
    movie = Movie.find_or_create(session, title)
    
    # Avoid duplicates
    existing = session.query(Review).filter_by(url=url).first()
    if not existing:
        review = Review(movie_id=movie.id, ...)
        session.add(review)
        session.commit()
```

## Important Notes

### Character Encoding
- All files use UTF-8 encoding
- Finnish characters (ä, ö, å) are common
- Handle Unicode star symbols (★, ⭐)

### Modular Design
- The project was refactored from 1070 lines to modular scrapers
- Each scraper is independent and testable
- Backward compatibility maintained via `scraper.py` wrapper

### Documentation
Extensive documentation exists in `docs/`:
- `PIKAOHJE.md` - Quick start guide (in Finnish)
- `REFACTORING.md` - Refactoring report
- `METASCRAPER_DESIGN.md` & `METASCRAPER_REPORT.md` - Discovery system docs
- `ERÄAJO.md` - Batch job documentation
- `README.md` - Data model and architecture

### Language
- Code: English (variable names, functions, classes)
- Comments: Mixed English/Finnish
- Documentation: Primarily Finnish
- User-facing content: Finnish

## Build and Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/test_scraper.py -v

# Start Flask app
python3 src/app.py
# Access at http://localhost:5000

# Run batch update
cd src && python3 batch_update.py
```

## API Endpoints

- `GET /` - Web UI displaying all reviews
- `GET /api/reviews` - JSON: all reviews
- `GET /api/reviews/<id>` - JSON: single review
- `GET /health` - Health check

## Key Dependencies

- `beautifulsoup4>=4.12.0` - HTML parsing
- `requests>=2.31.0` - HTTP requests
- `flask>=3.0.0` - Web framework
- `sqlalchemy>=2.0.0` - ORM
- `pytest>=8.0.0` - Testing (dev dependency)

## Best Practices for Contributing

1. **Minimal Changes**: Make surgical, focused changes
2. **Test First**: Write tests before implementing features
3. **Documentation**: Update relevant docs when changing functionality
4. **Consistency**: Follow existing patterns in the codebase
5. **Modularity**: Keep scrapers independent and focused
6. **Error Handling**: Handle edge cases gracefully
7. **Encoding**: Always use UTF-8, handle Finnish characters properly

## Common Tasks

### Debug a Scraper
```python
# Save problematic HTML
with open('/tmp/debug.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

# Test interactively
from scrapers import ExampleScraper
scraper = ExampleScraper()
review = scraper.parse_file('/tmp/debug.html')
print(review.to_dict())
```

### Add Test Data
1. Save real HTML to `tests/test_data/source_casename.html`
2. Anonymize if needed (remove personal data)
3. Reference in test with relative path

### Update Database Schema
1. Modify models in `src/models.py`
2. Update `src/init_db.py` if needed
3. Test with fresh database
4. Document changes in `docs/README.md`
