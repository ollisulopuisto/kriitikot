## 2026-11-20

- Match HS preview subjects to an existing film repeated in independent metadata fields. Read explicit headline star verdicts when body stars are absent; omit unrated HS reviews. Remove the per-article preview allowlist.

## 2026-11-20

- Publish validated imports from completed partial scraper batches, then visibly fail/report remaining source errors. Fatal errors and failed validation still block publication.

## 2026-11-20

- Require source-specific film facts across seven scrapers instead of silently creating films from editorial headlines, SEO titles or keywords. Headline-only previews fail closed.

## 2026-11-20

- Treat incomplete discovered review identities/authors/ratings as source errors,
  not silent skips or placeholder critics. Validate before database writes.
- Read Film-O-Holic's current structured film/rating and article author metadata,
  retaining legacy markup and rejecting incomplete review identities.

## 2026-11-20

- Repair seven Episodi headline-as-film-title rows: merge four into existing films,
  rename three, preserve every review, and remove invalid headline-derived ticket links.
- Discover IS article candidates without author/headline allowlists; classify
  articles under a bounded request budget with persistent backlog, retries,
  exclusion rechecks and separate outcome statistics.
- Require IS film-subject evidence, author and stars instead of generic headlines.

## 2026-11-20

- Place desktop sort and slider headings beside their controls, reducing the
  filter header from 173px to 128px at 1600px. Keep phone/tablet controls intact.
- Episodi titles now come from the film card or structured Movie subject, never
  the article headline. Conflicting identities fail closed.
- IS discovery includes Kari Järvinen. Non-review and TV/streaming exclusions
  are skips, while missing payloads remain errors.
- HS can use an explicit rating from a public review headline; missing film facts
  require an individually verified article mapping and matching public metadata.
- Publication chips and critic publication labels have full-name tooltips and
  accessible names, including mobile cards loaded after the first batch.

- Move desktop critic favourites beside the review count and remove the unused
  top heart row. Keep phone review cards unchanged.

- Compact filter header: three desktop columns, two rows, shorter sorting
  labels, readable minimum filters and smaller publication chips.
- Keep mobile controls touch-sized and allow scrolling through filters on short
  screens. Favourite switches now have clickable labels and keyboard focus.

# Changelog

## [Unreleased]

- Keep lazy-loaded pagination working when a review has no publication name; the mobile label stays empty rather than throwing on null.
- Keep published reviews in reviews.json when their publication row is missing. Preserve null publication fields and the single scalar-query export. Real SQLite regressions cover dangling IDs and deleted publications.

## [2026.11.09.1] - 2026-11-09

- Fixed: with one critic selected, "Lataa lisää" threw the critic column to the far right edge of the table. The fixed (sticky) header is a clone of the table header; it was rebuilt while the filler column was missing and froze the filler column's momentary pixel width, so the clone stretched and pushed the critic away from its cells. The clone now lets the filler column take the remaining width and is rebuilt whenever the filler column is added or removed. Filler cells are also added to every row (including hidden ones) and re-synced after "Lataa lisää", so loaded rows no longer lack them. Regression tests in `tests/frontend/critic-filler-column.test.js`. `APP_VERSION` bumped from 2026.10.05.2 (it had not followed the changelog).

## [2026.11.02.2] - 2026-11-02

- README korjattu: live-sivuston osoite on https://kriitikot.sulopuis.to/ (mukautettu domain, docs/CNAME), ei enää ollisulopuisto.github.io/kriitikot. Vanhenevat lukemat (~800 arvostelua / ~230 elokuvaa) ja lähdesijoitus (11) korvattu pysyvällä sanamuodolla - ajantasaiset määrät näkyvät live-sivustolla. Päivitysvälin maininta (6 h) korvattu viittauksella workflow-tiedoston aikatauluun, jottei numero pääse vanhenemaan.

## [2026.11.02.1] - 2026-11-02

- Frontend test timeouts on CI fixed: facet top-up tests render up to ~125 movies through jsdom and exceeded vitest's 5s default on the shared runner (error annotations "Frontend tests failed" on the scheduled run, issue comment automation fired) even though the suite passes locally. vitest testTimeout is now 20s with headroom; no production code changed.

## [2026.11.01.1] - 2026-11-01

- Facet-aware pagination in bounded batches of 10: selecting a critic, outlet, star minimum, review-count minimum or favorites auto-loads movies until the first batch of 10 matching reviews can be shown, and only that batch is visible. "Lataa lisää" reveals the next batch of 10 matching reviews under the active facets (loading more data when needed) and hides when no matches remain. Batches are counted in matching reviews but cut only at whole-movie boundaries, so a movie with several matching reviews is never split and a batch can slightly exceed 10. Clearing facets restores the previous unfiltered window.
- Outlet facet fixed for HS, KSML, IL, IS, SK, TS and Film-O-Holic: reviews.json carried full publication names while facet buttons use short codes, so those outlets matched nothing. reviews.json gains a `publication_short` field and the UI normalizes both forms when matching.

## [2026.10.05.2] - 2026-10-05

- `llms.txt` describes the site and its review data (reviews.json, RSS) for AI assistants and AI search.

## [2026.10.05.1] - 2026-10-05

- Search engines and AI search crawlers can find the site: `robots.txt` allows all crawlers and points to a new `sitemap.xml`.
- The page declares its canonical address (kriitikot.sulopuis.to) and carries schema.org structured data.
