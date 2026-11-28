# Settled mobile center-row star cue

Separate from search placement PR132. No click/tap handling changed. Only touch
phones/tablets<=768px and no-preference motion. After scroll/touchend settles
200ms, choose the fully visible review row closest to viewport center within a
central30%band. Animate only its existing star paint/shadow; no content reveal,
no row/card size changes, no repeated loop/glint. Remove cue800mslater or on
any new scroll/touch/resize/hidden/motion change. Once per movie+critic per visit,
including when lazy/windowed nodes are replaced. No storage or network.

Real Chrome at320/390/768touch verifies nearest-only, settled activation,
once-per-row, unchanged row bounds and link href, reduced-motion static. Actual
390pxbefore/active pixels inspected. Unit tests cover timing, nearest vs DOM
order, lazy insertion, hidden rows, touch suppression, desktop/motion gates and
cleanup. Existing shared filter/state remains untouched. Complete Python suite
440pass1skip; JavaScript suite75pass before third focused test (now3focused).
Own adversarial review traced lazy cards/windowing, filter hide visibility,
resize, preference changes, review link default and duplicate critic rows.
Source/checked-in docs assets synchronized narrowly, no data regeneration.
No merge/deploy. Existing search-placement PR132not included on this branch.

Follow-up: browser event traces exposed initial resize consuming the one-shot cue
before any user scroll. Added failing-first resize/visibility-before-scroll
regression (first scroll failed before fix), changed non-scroll lifecycle events
to cancel only, and replaced fixed 500ms browser wait with active-class condition.
Five consecutive full 320/390/768 runs pass with normal automatic startup.
78 JavaScript tests pass, 440 Python pass and 1 skip.
