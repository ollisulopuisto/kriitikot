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

## Review follow-up

The first Devin analysis completed on 8e8bdbb with a real forced-colors/print defect and a request to also check untouched published/lazy placement. Independently reproduced the first defect in Chrome and inspected the missing ratings. Print and forced-colors now use the already-present awarded-star text, monochrome system ink and no glow, so background suppression cannot erase the rating. Normal screen drawing is unchanged.

The second pre-push adversarial pass covered entry/exit of both background-free modes, linked and unlinked counts 1–5 at all four widths, source/published parity and restoration to screen styles. Added untouched published and lazy row/card samples alongside the catalog-independent exhaustive matrix, plus a background-disabled PDF capture. Re-ran frontend, Python and both browser suites; all remain green. Inspected forced-colors, print and normal-screen pixels before pushing.

## Second review follow-up

Strengthened the fallback oracle to reject hidden or zero-opacity stars and ancestors, and require positive glyph bounds. Negative controls exercise both visibility and opacity on a star and its rating ancestor, with transitions disabled during the control. Added pixel-difference checks between real fallback ink and the same rating with only its stars hidden. Existing PDF and full-page captures are also visually inspected. Wrapped all browser script lines to 79 characters and fixed set spacing.

The third pre-push pass covered fallback success, deliberately hidden failure, restoration, both media modes and source/published parity. Frontend 72, Python 321 plus 1 skip, rating/browser matrices and search regressions passed again. This follow-up changes tests and notes only, not the screen design or hover behavior.

## H6 implementation, owner approved

The owner approved building H6 and merging #112 on November 21. This supersedes the earlier no-merge restriction for this PR only, subject to tests and review.

Only the star paint scales 100% to 130% in 250ms on a fine hover pointer. The star-shaped ground shadow stays at +4/+6px with 1.2px blur, fading from zero to 28% opacity. Background, hit area and star anchors stay fixed. It holds while actually hovered and settles in 420ms on exit. The five-second hold and three-second row stagger were video demonstration timing, not a UI timer. Touch, reduced motion, print and forced colors stay static; print/forced colors omit the shadow.

Fourth pre-push adversarial pass: reviewed source/published template and lazy renderer parity, preserved exact awarded text, linked and unlinked hit areas, quick enter/exit/re-entry, hold beyond five seconds, clipping at 130%, source/published CSS and text fallback modes. Added separate paint/shadow structure assertions and real-Chrome H6 checks at 320/390/900/1600 with pointer and touch, reduced motion and interrupted transitions. Existing select/edit/clear/order/restore and delayed-result checks still pass. No filter or loader logic changed. Inspected actual raised 3/5 phone and 5/5 desktop pixels.

Tests: frontend 72 passed, Python 321 passed/1 skipped, rating geometry and search browser suites green. Run `WIDTH=390 python scripts/check_rating_hover.py`, repeat at 320/900/1600; set `TOUCH=1` for touch contexts. This H6 follow-up adds no scrape, data generation or deployment path.

The prior review also asked for dark forced-colors combined with print. Added that mode, asserted actual black print ink, and set print paint to black with forced-color adjustment disabled only on the glyph. This preserves system colors on screen while keeping paper ratings visible. Rechecked mode entry/exit and hidden-star negative controls before the follow-up push.

H6 review triage: fixed the smoke output path to a configurable writable /tmp default. Extended fallback hidden/opacity negatives to the new nested paint node, not only its slot and ancestor. Moved shadow clipping to a child pseudo-element so the outer blur is not clipped to a sharp star. The five-star tips' slight overlap at 130% is intentional H6 fidelity: it was present in the approved H5/H6 video, inspected at peak, and stays within the cell; no geometry change made for that investigate point. Combined dark forced-color print was already fixed in the preceding commit. Repeated adversarial review and regression checks before pushing these follow-ups.

Final review follow-up: both smoke scripts now use private, unique temporary output directories unless a screenshot destination is explicitly supplied. Hover checks compare real pixels with shadow-only visibility disabled, so absent shadow paint fails even when parent opacity is correct. Print checks rasterize background-disabled PDFs with and without star paint and assert an ink difference; this checks the actual PDF output, not merely screen media. The normal and dark-forced print outputs were inspected too. These follow-ups change verification only, not H6 geometry or behavior. Slight five-star overlap remains an explicitly adjudicated design choice matching the owner's approved mock.

Last verification review: PDF assertions now use five isolated, labeled-by-order 1–5 specimens and require rasterized ink difference in each specimen's own bounds, so one visible rating cannot satisfy another. Hover script documents Pillow and Chrome prerequisites. This is test-only; no further product change.

The print verification keeps both complementary checks: the untouched published page printed with backgrounds disabled, and each isolated rating's raster bounds. Source CSS reads declare UTF-8 rather than relying on locale. Rechecked both modes and per-rating ink before pushing this verification-only follow-up.
