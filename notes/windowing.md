# Review view windowing

The desktop body windows both movie rows and critic cells. Movie names and critic headers keep the existing pinned behavior. Phones window whole cards vertically, never their review columns. Overscan extends 1.5 viewports in the direction of travel and 0.5 behind it. Same-height row/card skeletons preserve the page geometry during a jump.

Original interactive nodes are parked off-document, not cloned or destroyed. A focused row/card remains mounted. Before filter, sort or pagination code reads its logical collection, `reviewWindow.prepare()` restores it synchronously. The next animation frame snapshots the new result and parks offscreen content again. Delayed filler-column refreshes are coalesced and use the same boundary. This keeps the current filter semantics and favorites storage without creating a second competing filter model.

This is connected-DOM virtualization, not a bounded object cache. Loaded nodes remain retained. Filter operations still process the full loaded collection. Do not describe this as a heap-memory reduction or a proven speedup.

The complete-view switch restores all loaded results for assistive technology and browser text search, with normal pagination still available. Printing temporarily restores the loaded collection too. Row/column indices preserve logical ordering in the windowed table. A real screen reader has not been tested; the explicit full-view fallback is important.

## Local measurement

Single before/after runs, headless local Chrome, desktop 1600 x 900 and phone 390 x 844, 1,072 reviews / 312 films / 90 critics. This is not a device performance study. No production scrape or deployment is used. Raw readings are in `tests/performance/windowing-{baseline,after}.json`.

| Reading | Before | After |
| --- | ---: | ---: |
| Desktop initial connected elements (60 films loaded) | 10,822 | 2,216 |
| Desktop elements after loading all films and scrolling | 55,822 | 4,276 |
| Desktop connected body cells after scrolling | 28,704 | 1,302 |
| Phone connected elements after scrolling | 17,553 | 1,527 |
| Phone mounted cards after scrolling | 312 | 8 |
| Desktop p95 frame interval in 60-step scroll | 27.4 ms | 30.9 ms |
| Phone p95 frame interval in 60-step scroll | 16.8 ms | 16.8 ms |
| Desktop JS heap after scrolling | 8,371,728 bytes | 8,541,476 bytes |
| Phone JS heap after scrolling | 6,814,280 bytes | 7,047,156 bytes |
| Desktop synchronous load-all plus settle | 13,417.7 ms | 14,096.8 ms |
| Phone synchronous load-all plus settle | 579.5 ms | 832.2 ms |

The supported benefit is a roughly 92% smaller connected DOM after scrolling. This run did **not** demonstrate faster scrolling or lower JS heap use. Mounting and measuring has a cost; the existing full-collection filter/pagination path remains expensive on desktop. Browser/GPU/native DOM memory and real mobile hardware are **unmeasured**. JS heap is not total browser memory. The added full-view control increases document height by 48 px on desktop and 93 px on phone; windowing did not change the content's remaining height.

## Checks

- `npm test`: frontend behavior plus viewport-window unit tests.
- `pytest -q`: Python regressions and scraper fixtures.
- `python scripts/check_windowing.py`: real Chromium windowed/full-view state comparisons across publication, stars, favorites, reset, critic/movie sorting and critic selection. Also tests horizontal cell/header alignment after column hiding, focus retention and Tab, print restoration, breakpoint changes, original data count and directional boundary pagination. Screenshots are saved for inspection. Requires Playwright and local Chrome.
- `python scripts/measure_windowing.py --label after`: repeat the local measurement. Set `SCREENSHOT_DIR` and `CHROME_BIN` as needed. The measurement deliberately loads all existing data; it does not scrape or publish.

Manual inspection covered desktop first view, horizontally and vertically scrolled desktop with pinned headers/names, and phone first/scrolled cards. All retain the light palette. A real screen reader, Safari/Firefox and physical mobile devices are **unmeasured**.

## Review follow-up

Full view and printing remove window-only accessibility counts/indices so native table order cannot become stale after sorting or appending. Automatic pagination follows each actual downward page movement, including scrollbar navigation; proximity changes alone and upward movements cannot trigger it. After filter/layout mutations there is a short preload suppression interval. Programmatic downward navigation is intentionally treated like native scrollbar navigation. Appended batches inherit the selected alphabetical order. The critic registry is read only from the original table, never its pinned-header clone. Ordinary scrolls skip geometry reads for the inactive view. Browser checks derive catalog totals from the loaded JSON instead of assuming a forever-fixed catalog. The Chrome executable override is honored by both scripts.
