# Changelog

## [2026.11.01.1] - 2026-11-01

- Facet-aware pagination: selecting a critic, outlet, star minimum, review-count minimum or favorites auto-loads more movies until at least 10 matching reviews are visible. "Lataa lisää" loads the next batch of matching reviews under the active facets instead of a raw 30-movie batch, and hides when the remaining data has no more matches. Clearing facets restores the previous unfiltered window.
- Outlet facet fixed for HS, KSML, IL, IS, SK, TS and Film-O-Holic: reviews.json carried full publication names while facet buttons use short codes, so those outlets matched nothing. reviews.json gains a `publication_short` field and the UI normalizes both forms when matching.

## [2026.10.05.2] - 2026-10-05

- `llms.txt` describes the site and its review data (reviews.json, RSS) for AI assistants and AI search.

## [2026.10.05.1] - 2026-10-05

- Search engines and AI search crawlers can find the site: `robots.txt` allows all crawlers and points to a new `sitemap.xml`.
- The page declares its canonical address (kriitikot.sulopuis.to) and carries schema.org structured data.
