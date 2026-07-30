# Kriitikot — Agent Reference

Finnish movie review aggregator: scrapes reviews from media sites, stores in SQLite via SQLAlchemy, serves via Flask.

## Stack

- **Language:** Python 3.9+
- **Web:** Flask (`src/app.py`)
- **DB:** SQLite + SQLAlchemy ORM (`src/models.py`)
- **Scraping:** BeautifulSoup4, requests
- **Tests:** pytest

## Key Commands

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run single test
python3 -m pytest tests/test_scraper.py::test_hs_scraper_basic -v

# Start Flask dev server
python3 src/app.py          # http://localhost:5432

# Batch import (all sources, 10 reviews each)
cd src && python3 batch_update.py

# Import from one source
cd src && python3 batch_update.py --source hs --limit 5

# Full update (20 per source)
cd src && python3 batch_update.py --full

# Generate static site for GitHub Pages
python scripts/generate_static.py
```

## Architecture

```
src/
├── scrapers/           # One module per publication
│   ├── base.py         # Review dataclass + BaseScraper ABC
│   ├── __init__.py     # Registry dict + scrape_review() helper
│   ├── hs.py           # ... (8 active scrapers)
│   └── ...
├── app.py              # Flask app (templates/, static/)
├── models.py           # Movie, Critic, Publication, Review tables
├── discovery.py        # MetaScraper — finds review URLs per source
├── discovery_importer.py  # Orchestrates discover → scrape → save
├── batch_update.py     # CLI batch import script
├── movie_normalizer.py # Fuzzy title matching (threshold 0.9)
├── metadata_fetcher.py # TMDB/IMDB/Letterboxd enrichment
├── services/
│   └── data_service.py # Query helpers for Flask views
└── scraper.py          # Backward-compat wrapper (deprecated)
```

**Data flow:** `discovery.py` finds URLs → `scrapers/` parse HTML → `discovery_importer.py` saves to DB via SQLAlchemy.

**DB schema:** `Movie` ←1:N→ `Review` ←N:1→ `Critic`, `Review` ←N:1→ `Publication`. Reviews deduplicated by `source_url` (UNIQUE). Movies fuzzy-matched with `SequenceMatcher` at 0.9 threshold.

## Active Sources (11)

`hs`, `ksml`, `il`, `ts`, `sk`, `is`, `episodi`, `muropaketti`, `filmoholic`, `kulttuuritoimitus`, `demokraatti`

Disabled: `kaleva` (paywall), `seura` (parsing too hard — module exists but is not registered)

Registry: `src/scrapers/__init__.py` → `scrapers` dict.

## Adding a New Scraper

1. **Create module** in `src/scrapers/<name>.py`:
   - Inherit `BaseScraper`, call `super().__init__(publication_name="...")`
   - Implement `parse_html(html_content, source_url) -> Review`
   - Rating: `int` 1-5 or `None`
   - Use `self.get_soup(html)` for BS4 parsing

2. **Register** in `src/scrapers/__init__.py`:
   - Import the class, add to `scrapers` dict, add to `__all__`

3. **Add discovery** in `src/discovery.py`:
   - Add URL to `CATEGORY_PAGES`
   - Add `elif` branch in `find_review_links()` with `_find_<name>_reviews()` method

4. **Add to importer** in `src/discovery_importer.py`:
   - Import + add to `self.scrapers` dict in `__init__`

5. **Add publication to DB** (one-time):
   ```python
   from models import get_session, Publication
   session = get_session()
   if not session.query(Publication).filter_by(name='NewPub').first():
       session.add(Publication(name='NewPub', short_name='newpub'))
       session.commit()
   session.close()
   ```

6. **Test:** Save sample HTML to `tests/test_data/<name>_review_1.html`, write test in `tests/test_scraper.py`, run with pytest.

## Shared helpers on `BaseScraper`

Use these instead of re-implementing extraction (`src/scrapers/base.py`, covered by
`tests/test_base_scraper_helpers.py`):

| Helper | Purpose |
|---|---|
| `count_stars(text, max_stars=5)` | Count `★`/`⭐`; `None` if none |
| `parse_rating(text)` | Stars → `X/5` → `X tähteä` → Finnish numeral ("neljä tähteä") |
| `extract_jsonld(soup, types=...)` | First matching ld+json block; handles dict, list **and** `@graph` |
| `extract_author(soup, ld_json, exclude=())` | `article:author` → JSON-LD author → `meta[name=author]` → `rel=author`; `exclude` rejects publication names |
| `meta_description(soup)` | `og:description` → `meta[name=description]` |
| `extract_next_data(soup)` | Parse `<script id="__NEXT_DATA__">` |
| `extract_paragraphs(soup, ...)` | Body text from `<p>`; params: `selectors`, `min_length`, `skip_phrases`, `skip_parent_classes`, `max_chars`, `limit` |

Keep **site-specific locators** in the subclass; share only the sub-steps.

See existing scrapers for reference:
- **Simple HTML:** `scrapers/hs.py`
- **JSON API (WordPress):** `scrapers/episodi.py`
- **Complex rating extraction:** `scrapers/muropaketti.py`
- **Double-encoded UTF-8:** `scrapers/il.py` (stars appear as `â\xad\x90`)

Key patterns:
- Title: prefer `og:title` meta or JSON-LD over `<h1>` (often contains headline, not movie name)
- Rating: image filenames and site-specific markup still need per-scraper handling
- Text: skip paragraphs < 30 chars, skip boilerplate ("lue myös", "jaa artikkeli")
- Uppercase titles: convert to title case if `title.isupper()` and ≤4 words

## Frontend notes

- **Review data is lazy-loaded**: the page fetches `reviews.json`; only the first 30 movies
  are server-rendered. Do not inline the full dataset into `index.html` again.
- **Desktop table rows live in `<template id="desktop-rows">`** inside `<tbody>`.
  `app.js` clones them only at ≥769px, so phones never build those ~2,500 cells.
  Anything that walks `tbody.rows` must tolerate an empty tbody.

## Gotchas

- **Duplicate reviews:** prevented by `source_url` UNIQUE constraint — always pass canonical URL
- **Finnish characters (ä, ö):** always use `encoding='utf-8'` when reading files; watch for double-encoding
- **Kaleva disabled:** paywall — code commented out in registry
- **`scraper.py` is deprecated:** use `from scrapers import ...` not `from scraper import ...`
- **DB location:** `reviews.db` at project root (SQLite file)
- **Flask template folder:** `../templates` relative to `src/app.py`
