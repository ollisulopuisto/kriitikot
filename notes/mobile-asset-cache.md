# Mixed-release cached assets

Both iPhone reports reproduce in Chrome390 with current HTML and predecessor
05d22e8 CSS/app.js/ui.js: wrapper gets32px side margins (x70,width250 rather
than aligned x38,width314), and active search collapses to plain Hakuehdot with
no X. Fresh current assets work. No service worker in the application. This
supports stale unversioned asset URLs as the common cause, not native input
padding. Cannot inspect the user's actual browser cache to prove its contents.

All five CSS and six JS references now include16hex SHA256 content versions,
rendered by Flask and preserved in checked-in static HTML. Unchanged files
keep their URL; changes invalidate the corresponding URL. No CSS geometry or
search behavior changed. Old HTML can remain cached until refresh, but a new
page cannot reuse the predecessor's unversioned asset URLs. Query versioning
avoids copies/renames and works on Pages subpaths. Generator renders the same
template, and tests verify docs/source asset hashes match contents.

Failing-first: three asset tests fail before implementation. Browser stale-cache
regression fails input alignment with unversioned HTML, passes with hashed URLs.
443Python pass/1skip,80JS tests pass. Existing search and star320/390/768 browser
suites pass. Actual390px stale/fixed expanded and active pixels inspected.
WebKit runtime cannot launch due missing system libraries, so iOS-specific
confirmation remains unverified. Own review traced template generation, Flask,
static copying, all11 references, docs parity and future asset modifications.
No scrape/data regeneration/deploy or merge.
