# Bolt's Journal - Critical Learnings Only

This journal contains critical learnings to avoid mistakes and make better decisions.

## 2026-11-05 - Lazy data migration leaving dead serialization on server routes
**Learning:** When client-side architecture evolves to lazy-load datasets via dedicated endpoints (such as `reviews.json`), check server view context builders (`get_index_data`). Often the previous inline serialization (`all_reviews_json`) is left behind, serializing megabytes of JSON and retaining large strings in memory on every request even though templates no longer reference them.
**Action:** Audit view contexts after lazy-loading refactors to verify all returned keys are actually referenced in templates.
