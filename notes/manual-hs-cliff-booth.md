# One-time HS review metadata addition

Owner explicitly asked to add the restored Tarantino HS review manually on
2026-11-28. This is a single-record exception, not a parser/admission-policy
change. No Episodi change or deletion.

- Source: https://www.hs.fi/popkulttuuri/art-2000012401104.html
- Author: Veli-Pekka Lehtonen, HS.
- Rating: 4, explicit Finnish numeral rating in the headline.
- Publication date: 2026-11-26. Stored midnight represents date precision only.
- Target: existing movie374, The Further Mis-Adventures of Cliff Booth.
- Supporting source: https://muropaketti.com/elokuvat/elokuva-arvostelut/arvio-cliff-booth-on-quentin-tarantinon-elokuvaksi-yllattavan-tylsa-edes-brad-pitt-ei-pelasta-vuoden-2019-hitin-jatko-osaa/

The live HS preview describes Brad Pitt returning as Cliff Booth, a Tarantino-
written sequel to Once Upon a Time in Hollywood, with an ageing father/son
relationship. Muropaketti's live full review explicitly identifies that same
sequel, Tarantino script, Pitt's character and father/son story with the film
facts title. Existing DB movie374 has that identity and metadata; the preceding
Hollywood film mentioned in HS's caption is not the review subject. HS's preview
still lacks its own film-facts title, so automatic HS admission remains unchanged.

No paywall text is imported. review_text and scraped_at are NULL. The new critic
was absent, so the DB diff is exactly one critic insert and one review insert;
all pre-existing rows/columns unchanged. No movies/publications inserted.

Verification: dry-run, transactional apply, idempotent rerun, row-by-row DB diff,
foreign_key_check and integrity_check. Seven isolated tests cover dry-run/apply,
idempotence, existing-critic reuse, target/publication identity, ambiguous critic,
conflicting source URL and same-film/critic conflict. Full backend suite passes.
The real Flask /, /reviews.json and /rss.xml return 200 with the updated DB;
reviews.json contains review1148 with the correct title/byline/source/rating.
Generated docs are deliberately not committed. This PR alone is not a claim that
the live site has published it or that the source-health issue is fixed.
