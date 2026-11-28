# Mobile search in Hakuehdot

The search input now belongs to the same collapsing panel as the remaining
mobile filters. Input handling, shared query state, reset and desktop sync stay
unchanged. The field is hidden when collapsed and first in the panel when open.

Verified with real Chrome at320,390,768px, desktop900/1000/1600px. Updated browser
script failed before markup/CSS fix.73Vitesttests and440pytesttests pass,1skip.
Screenshot pixels inspected at390px, closed and open. No horizontal overflow.
Own review traced delegated handlers, input sync, filter reset, focus and later
lazy-rendered cards. No new search state. Source/checked-in docs moved together,
no regeneration or production data changes. Supersedes PR131placement only.
Open/recentPRoverlap checked, nothing open. No merge/deployment performed.

Approved active-summary option B: collapsed query plus count of other active
filter groups; count-only fallback without query. Amber active bar, left
chevron and separate right clear-X. Existing resetAllFilters owns all clearing;
no second filter state and no results button. Summary reads shared facet state
without calling reviewWindow.prepare, so opening/updating it cannot unwindow
rows. Publications count as one group regardless of selected publication count.
Browser coverage at 320/390/768 includes query+stars, count fallback, keyboard
clear/focus, long query ellipsis/no overflow, no-result/reset and desktop switch.
74 JS tests and 440 Python tests pass, 1 skip. Pixel inspection at390 covers
inactive/active/expanded. Own adversarial review checked safe textContent,
accessible full query, separate buttons, all facet/reset consumers and source/
docs parity. Existing panel can push results below fold; intentionally no
additional results button. Neither merge nor deployment performed.

Review follow-up FIND-132-1: separate non-shrinking count span preserves +N
when the query truncates. Reviewer regression failed against the previous head,
then passed with the patch. Label-in-name fixed by starting aria-label with the
visible label and suffix, retaining full query and disclosure action. 75 JS tests,
440 Python pass/1skip, browser320/390/768 passes. Actual320/390 long-query pixels
inspected: ellipsis only affects query, +1 and clear remain visible. Own review
checked empty suffix/open state, fallback count and independent clear target.
