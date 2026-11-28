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
