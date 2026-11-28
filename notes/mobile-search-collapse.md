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
