# Scheduled scrape health

Validated imports still publish when a few individual articles fail. Per-item
failures remain in the batch log and source warnings appear in the job summary.
One `Scraper source health` issue records the latest affected sources. It updates
in place, closes on recovery, and reopens on later failures. No repeated comments.

Publication, validation, tests and fatal batch errors still fail the workflow.
After successful publication, source-wide failures also fail the health gate:
discovery errors, missing scraper/publication, or all discovered items failing.
For partial item failures, three consecutive degraded batches for the same source
are treated as sustained loss. A rerun of one batch does not increment this count.
Healthy completed batches reset that source's streak. State is in the issue,
not in the database or cache. Invalid health state fails visibly.

The batch exit contract remains 0 healthy, 2 completed partial, 1 fatal, 130
interrupted. This does not repair the underlying Episodi/Muropaketti parsers.
