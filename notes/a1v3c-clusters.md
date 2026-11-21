# A1v3c rating constellations

Implements the selected light-palette A1v3c study. Ratings 1–4 keep A1v2's positions; five stars form two above and three below. Each star is square and proportional, inside a fixed 100 × 64 px rating area. Gold has a thin dark edge. Five-star glow belongs to the stars, not the face. Hover does not move or enlarge the rating.

The existing five DOM slots, numeric labels, links and awarded-star text are unchanged. Hidden empty slots paint no extra stars. Desktop cells reserve the drawing plus padding, and the 320px phone lane reserves the full 100px width.

## Pre-push adversarial review

Reviewed CSS cascade, source/published parity, server/lazy rendering and downstream text-based star counting. Tested both linked and unlinked 1–5 ratings through real desktop/mobile ancestors at 320, 390, 900 and 1600px, including hover, keyboard focus, reduced motion and clipping. Negative controls move stars outside the face and collapse a clipping ancestor. The geometry check does not depend on the catalog containing every rating.

Reviewed state transitions across select, query edit, clear, ordering, restore, delayed catalog results and publication filtering. Existing search checks exercise these transitions. Added repeated star-threshold edits and clears against both responsive trees. No loader, retry or partial-failure implementation changed; existing frontend regression tests remain green.

The review found two issues before the first push: a 100px drawing could invade its desktop neighbor when the old column width was retained, and gold fill alone missed 3:1 against a tinted cell. Reserved 116px desktop columns and added the selected design's dark gold edge, then tested computed geometry and actual edge color. Removed obsolete gradient/white-star rules, their stale contrast assertions and the unused previous geometry helper.

## Validation

- `npm test`: 72 passed.
- `.venv/bin/python -m pytest -q`: 321 passed, 1 skipped. The lower count reflects removal of 16 obsolete gradient/white-star tests, not skipped current coverage.
- `python scripts/check_rating_pills.py`: all 20 server/lazy and linked/unlinked variants per viewport passed at 320/390/900/1600.
- `python scripts/check_film_search.py`: 900/1600 selection, edits, sort, clear, pinned focus, publication and delayed-query checks passed.
- Inspected actual desktop and phone screenshots after cleanup, including the 1–5 scale and live-page context.

No scraping, database changes, site regeneration, deployment or merge is part of this PR. Merge requires the owner's explicit instruction.
