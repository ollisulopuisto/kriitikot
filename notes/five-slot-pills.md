# Five-slot rating pills

Implements the selected10E C sketch, pills only:1red,2orange,3yellow,4blue,
5green; existing gradient, rounded face, shadow and outlined white stars.
The larger glyphs fill a fixed five-slot face. Empty stars remain faint white.
The colored face is separate from its link target, preserving the phone's44px
tap height without enlarging the face to match it.

Server and lazy JS rendering both expose the real n/5 as an accessible image
label. Child slots are hidden from accessibility APIs. Empty stars are CSS
content, not DOM text: existing facets, critic averages, sorts and summaries
still count only awarded stars. No data or scraper changes.

Checks:
- pytest tests/, including server1-5slots, labels, palette and generated assets.
- npm test, including linked/unlinked JS1-5slots and low/high star filtering in
  both desktop rows and phone cards.
- python scripts/check_rating_pills.py: real Chromium at320,390,900,1600px;
  all five ratings linked/unlinked, fixed footprint, slot containment, page
  width, no page errors and minimum-star filter. Screenshots include the scale
  and actual site context. No scraping, writes or deploys.
- Broader check_windowing.py reached desktop filters/sorts/pagination checks,
  then Chrome crashed during its large print-media exercise. Not a passed full
  windowing rerun. That print check is unchanged by this patch.

Physical devices, other browsers and a screen reader were not tested. White
stars on the three light backgrounds still rely on their existing dark outline;
this is not a new WCAG compliance claim.
