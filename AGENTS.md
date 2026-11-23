# Kriitikot — Agent Reference

## Retiered hover lift and five-star glint, 2026-11-22

Hover lift no longer grows 1px per star: ratings 1 and 2 lift 0.5px, 3 and
4 lift 3px, and 5 lifts 6px while keeping the 1.05 scale. Five stars add a
one-shot 550ms left-to-right glint across the constellation on hover entry
(fiveStarGlint keyframes carry the resting glow so it never drops out),
staggered 70ms per star in x order; the animation lives inside the
hover/pointer/no-preference media query, so touch and reduced motion stay
still. scripts/check_rating_hover.py pins the LIFT map, the glint
animation name per rating and the glow's return to rest after it ends.

## Bare rating clusters and hover values, 2026-11-21

Remove the cluster wash, not the star colors, five-slot accessible text or H6
paint/shadow layers. Four-star positions are now (37,21), (63,21), (37,43),
(63,43), producing a smaller footprint than five stars. Shared lazy rendering
and both server templates include the rating in review-link titles.

Regression: pytest, npm test, scripts/check_rating_pills.py and
scripts/check_rating_hover.py. The Chrome checks cover transparent faces,
all rating footprints, server/lazy links, pointer/touch/reduced motion and
forced-color/print fallback. Generate docs with scripts/generate_static.py;
no scraping or production DB edits are needed.

Finnish movie review aggregator: scrapes reviews from media sites, stores in SQLite via SQLAlchemy, serves via Flask.

## Stack

- **Language:** Python 3.10+
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

## Audit follow-through, 2026-10-29

Index critic media/count summaries reuse the already eager-loaded published
reviews instead of one SQL query per critic. Isolated40criticfixture:51SQL
statements before,11after; exact count regression plus no-review critic and
pending-review exclusion covered. Full185Python testsPASS1skip;23JStestsPASS.
No wall-time/deployed speedup claim. Existing data_service typing/import lint
debt remains; broadruff is not green. reviews.db hash unchanged fromHEAD,
no scrape/model call, generatedPages writes, deploy or merge. Human merge pending.

## CI follow-through, 2026-10-30

Scheduled runs reported "Frontend tests failed" since 2026-10-25 (automation
comments on issue #19). Cause: Dependabot all-npm bump 936d34e (jsdom 30.1.3,
vitest 5.0.5) raised the devDependency engines floor to Node >=22.12; undici
8.12.3 calls zlib.createZstdDecompress at module load (Node 22.15+ only), so
on the workflow's Node 20 every vitest forks worker died at startup. Fix:
NODE_VERSION '20' -> '24' in scrape_and_deploy.yml (PR #67). Backend pytest
unaffected (185 passed, 1 skipped); 23 JS tests pass on Node 22. If frontend
CI fails again after a Dependabot bump, compare the workflow NODE_VERSION
against the engines floor in package-lock.json first.

## CI frontend test timeouts, 2026-11-02

The scheduled Scrape and Update run that deployed the facet pagination fix
(run 41384251805) succeeded as a deploy but carried "::error:: Frontend
tests failed" annotations: two facet tests (favorites intersection,
facet-autoload tail-exhaustion) exceeded vitest's 5s default testTimeout on
the shared runner. The workflow's test step annotates failures and comments
on tracking issue #19 but does NOT stop the deploy. Local runs were green
(33/33, slowest ~3.7s); the shared runner is simply slower with jsdom
rendering ~125 movies per top-up test. Fix: testTimeout 20000 in
vitest.config.js. If frontend timeouts reappear on CI, compare local vs CI
per-test durations before assuming a real regression; the heavy tests are
correctness tests over large synthetic datasets, not perf budgets.

## Facet-aware pagination follow-through, 2026-11-01

User report: clicking a critic showing "9 reviews" displayed only the already
loaded movies (1 of 9), and "Lataa lisää" ignored active facets. Root causes:
(1) the slider-window top-up (`rememberSliderWindow`/`topUpSliderResults`) was
wired only to the two sliders, not to critic/outlet/favorites facets or the
Load more button; (2) the top-up target was 30 visible movies, not matching
reviews; (3) the outlet facet matched nothing for HS/KSML/IL/IS/SK/TS/
FILMOHOLIC because reviews.json carries full publication names while the
facet buttons carry short codes.

Fix: all facet changes (critic click, outlet buttons, favorites toggle,
sliders, reset) go through the window top-up; with facets active the loader
pulls 30-movie chunks until the loaded data holds the current reveal target
of matching reviews (loadedMatchingReviewCount, pure-data over
allGroupedReviews), then applyFacetBatchVisibility (hooked at the end of
reconcileFacetVisibility) shows exactly one batch of FACET_REVIEW_BATCH=10
matching reviews and batch-hides the rest with data-batch-filtered. Batches
are counted in matching reviews but cut only at whole-movie boundaries: a
movie with several matching reviews is never split, so a batch can exceed
10 by the last movie's extra matches. Load more raises the reveal target by
10, loads more chunks if the loaded data lacks them, and hides when neither
batch-hidden cards nor tail matches remain (tailHasFacetMatches mirrors
reconcileFacetVisibility over the unloaded tail). Slider windows store
{offset, reveal} so facet toggles restore both. Publication matching
normalizes full names to short codes (PUB_FULL_NAME_TO_SHORT + new
`publication_short` field in Review.to_dict; reviews.json picks it up at
the next site generation, the client map covers legacy data until then).
Desktop + mobile verified with headless Chrome against generated docs/:
critic facet (Maria Lättilä) auto-loads all 291 movies and shows her 9/9
reviews with Load more hidden; outlet facet (HS, 152 matching reviews)
shows exactly 10 per batch, +10 per Load more click, final partial batch
150->152, button hides at the end, no duplicate (movie, critic) pairs at
any step; facet toggle-off restores the previous 60-movie window. 33 JS
tests pass (7 in facet-autoload.test.js incl. a whole-movie batch-boundary
test: 3 matching critics per movie reveals 12, then 21, then all 24 with no
duplicates), 185 Python tests pass, ruff shows only pre-existing debt. No
deploy, no docs/ regeneration committed, human merge pending.


## Pull request descriptions

Start with 2-4 short sentences explaining the change and whether it needs attention. Put implementation and test detail in a `<details>` block. Use `Agent details (model unknown, effort: maximum)` when the model cannot be verified; do not guess an identity.

## Compact header, 2026-11-20

Owner selected sketch 1: compact controls in the existing site palette in three desktop columns and
two rows. Tablet uses two columns with publications below; phone keeps its
existing collapsible panel with 44px controls and internal scrolling on short
screens. Removed accumulated desktop overrides rather than appending another
competing layout. Sort/filter IDs and JS behaviour are unchanged. Favourites
now have clickable labels and a visible keyboard-focus ring.

Regression commands: `uv run pytest` and `npm test`.
Optional real-Chrome geometry + interaction checks and screenshots:
`uv run --with playwright python scripts/check_header_layout.py`.
Set CHROME_BIN if Chrome is elsewhere; SCREENSHOT_DIR selects capture output.
No scraping or site regeneration is part of that check.

## Favourite beside count, 2026-11-20

The desktop favourite button now sits after the review count in
`.critic-bottom-row`; no dedicated heart/name-row padding remains. It is a
native button with the critic name in its accessible action label. The mobile
review-card placement is unchanged. Removed the accumulated identity/absolute
positioning overrides. Regression coverage includes no-count fixtures,
favourite persistence, no accidental critic filtering, native Space activation
in Chrome, and geometry. The optional Chrome script checks this too.

## Episodi data repair, 2026-11-20

`scripts/repair_episodi_titles.py` is a one-time approved mapping for seven rows.
Dry-run by default; --apply is transactional and idempotent. It guards source URLs,
original titles, merge targets, critic conflicts and foreign keys, preserving review
content and IDs. Four merges and three renames reduce316films to312, keeping1069reviews.
No source imports or author edits included. Regression: pytest tests/test_episodi_repair.py.

## Discovered review admission, 2026-11-20

A discovered candidate lacking a nonblank film title, named author or integer
1–5rating is an unresolved source/parser failure, not a successful empty import.
Unknown/publication-name/URL author placeholders are not real critic identities.
Admission validation runs before any movie/critic creation. Explicit source-level
non-review exclusions (such as the IS classifier) still skip normally. This guard
does not claim arbitrary nonblank headline titles are valid; source-title evidence
remains a separate audit. Regression: pytest tests/test_review_admission.py.

## Source film-subject evidence, 2026-11-20

Never substitute an editorial h1, SEO title, keyword or generic short paragraph
for film identity when source film facts are absent. TS uses its intro film name,
IL its title/country-year facts pair, KSML its film storyline lead, SK its
film/distributor endnote, Muropaketti its premiere block, Demokraatti its ELOKUVA
infobox and Kulttuuritoimitus its film metadata block. Missing facts fail parsing;
#101 reports such unresolved previews as source failures rather than silent skips.
This deliberately drops headline-only previews until independent title evidence
is supported. The historical IL paywall fixture is one such preview; its byline
still parses but the review is rejected. Paired positive film-facts tests and
saved live-source replays preserve current supported layouts. No DB changes or
live bulk imports. Focused regression: pytest tests/test_subject_evidence.py.

## Partial scraper publication, 2026-11-20

A completed batch with per-source failures exits2; fatal errors remain1 and
interruptions130. The workflow permits only exit2to continue through the existing
metadata, generation and single DB/docs commit path. It records the partial result
and import count in the summary, then fails after publication so the existing
failure issue remains visible. Failed tests, fatal batches, failed metadata or
failed generation/commit stop publication. No always()-push is introduced.
Regression: pytest tests/test_batch_exit.py, including actual bash exit handling.

## HS preview evidence, 2026-11-20

HS ratings prefer literal body stars, then an explicit 1–5 star verdict in the
film-review headline. No rating means no import, not a source outage. Missing
film facts can resolve only to one existing DB film repeated in at least two of
metaTitle, ingress and main-picture caption; the editorial h1 is not a film name.
Ambiguous titles and numbered/subtitled sequel continuations are rejected.
Regression: tests/test_hs_preview_identity.py, including captured Dry Leaf preview,
independent caption evidence, no-rating admission and short-title collisions.
No schema, workflow, production DB or generated-site change.
## Author-independent IS discovery, 2026-11-20

IS category cards are candidates, not reviews. Discovery collects all unique
same-origin article URLs without author/headline gates. The importer classifies
article tags, cinema evidence, film subject, author and stars; --limit counts
admitted reviews, not candidates. Each run makes at most40article requests,
spaced1second apart, and carries its backlog in data/is-discovery.json.
The queue caches explicit exclusions for7days and retries failures after12hours;
due failures come first, then oldest pending work and exclusion overlap. A failed cached item keeps the source
failure visible until resolved. The scheduled workflow persists only the public
queue file even if partial review publication is blocked. Cached success without
a saved ReviewURL is requeued, so failed deployments do not lose articles.
Tests use isolated temporary queue files and in-memory databases. Do not run a
live import just to test this code. Full regression: pytest; focused:
pytest tests/test_is_discovery_queue.py. No sitemap/backfill coverage claim.
## Film-O-Holic metadata, 2026-11-20

The current pages expose Review.itemReviewed.Movie and reviewRating JSON-LD,
plus article:author. The old rating meta/name=author paths alone now miss live
reviews. Prefer the structured film subject and shared author helper; retain
legacy h1/category, reviewer-span and rating-meta support. Missing identity,
author or valid1–5rating is a parser failure, not a silent rating-less skip.
Three failing-first regressions plus legacy tests pass. No DB import included.

## Explicit non-review and paywall outcomes, 2026-11-23

KSML previews with an explicit boolean isAccessibleForFree=false, a film-facts
title and a named byline, but no rating evidence, are now excluded without
failing the source. Missing access metadata, missing identity/byline, malformed
rating evidence and other parser failures remain failures. No unrated review is
imported. The owner approved this status-policy change on 2026-11-23.
Demokraatti festival-opening features require positive headline and body evidence;
review headlines, infoboxes and stars prevent exclusion. Unknown layouts still
fail rather than silently disappearing. Each excluded URL is logged with a reason,
and per-source reason counts are printed and exposed in source_exclusions.

Consumer trace: discovery importer before parser/admission/DB writes; source failure
counts consumed by batch_update exit status; unchanged partial-publication workflow.
Tests cover isolated DB outcomes, positive exclusions and ambiguous/corrupt inputs.
Regression: uv run pytest; npm test. No schema, workflow or generated-site changes.
