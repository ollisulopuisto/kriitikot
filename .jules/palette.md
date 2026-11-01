# Palette journal

## 2026-11-01 - kriitikot: star/review sliders had no keyboard focus indicator

The filter sliders (`input[type=range].slider` in templates/index.html) set
`outline: none` in static/css/filters.css and had no :focus or :focus-visible
style anywhere. Keyboard users tabbing to the star-rating and min-reviews
sliders got no visible focus indicator (WCAG 2.4.7).

Fix: added `.slider:focus-visible` with a 2px violet outline matching the
slider thumb color (#8b5cf6). CSS-only change, no behavior impact.
