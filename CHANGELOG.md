# Changelog

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
