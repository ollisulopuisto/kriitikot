# Episodi critic links, 25 November 2026

Source-verified plan, no live changes performed by this PR. Current GitHub-main
readonly dry-run changes only these review links, from placeholder Critic89:

| Review | Film | Existing target Critic |
|---|---|---|
|928|The Dog Stars|24, Jussi Huhtala|
|1032|The Social Reckoning|37, Jouni Vikman|
|1070|Dracula|37, Jouni Vikman|
|1112|You Can See Everything|21, Werneri Pihlajamäki|

Source URLs are in the adjacent manifest. Fetched25November2026 after parser121.
The script reuses exact existing names, never creates/renames/deletes critics.
Other named critics are not rewritten. Ratings, text, movie identity, dates,
publication and publication status stay unchanged. No schema migration.

Dry-run first against the current authoritative database:

    python scripts/repair_episodi_critics.py --database /path/to/reviews.db

Review the rows before applying. Do not apply before the owner has seen this
preview. Stop scheduled scraper writes during the repair and regeneration.
Apply requires a new backup path, never overwrites a backup:

    python scripts/repair_episodi_critics.py --database /path/to/reviews.db --apply --backup /path/to/reviews-before-episodi-repair.db

An immediate transaction rechecks IDs, URLs, film names, publication, current
critic and uniqueness. A SQLite backup captures committed data before changes.
No network calls occur. Rerun dry-run afterward: it should report an empty list.
Regenerating/publishing the site is a separate step, not performed by this script.
Restore from the backup only with scraper writes stopped and after checking that
no newer data would be lost. Keep the backup outside the repository.
