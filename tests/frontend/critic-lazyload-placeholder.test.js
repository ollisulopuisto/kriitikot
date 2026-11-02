import { describe, it, expect, beforeEach } from 'vitest';
import { setupDOM } from './test-helper';

describe('Critic lazy-load placeholder and caching', () => {
  // 80 elokuvaa; Susanna Bono arvostelee kaikki, Toinen Kriitikko vain joka 10. (8 kpl)
  const buildReviews = () => Object.fromEntries(Array.from({ length: 80 }, (_, i) => ['Film ' + i, {
    'Susanna Bono': [{ rating_stars: 4, source_publication: 'Episodi' }],
    ...(i % 10 === 0 ? { 'Toinen Kriitikko': [{ rating_stars: 5, source_publication: 'Helsingin Sanomat' }] } : {})
  }]));

  const createTestHTML = (reviewsData) => `
    <div class="container">
      <script id="all-reviews-data" type="application/json">${JSON.stringify(reviewsData)}</script>
      <script id="movie-meta-data" type="application/json">{}</script>
      <div class="desktop-filters">
          <input type="range" id="min-reviews-slider" min="1" max="5" value="1">
          <span id="min-reviews-value">1</span>
          <input type="range" id="star-filter-slider" min="1" max="5" value="1">
          <span id="star-filter-value">Vähintään ★</span>
          <div id="reset-filters-desktop" style="display:none"></div>
      </div>
      <div id="review-container-desktop">
          <table>
              <thead>
                  <tr class="critic-row">
                      <th class="movie-col">Elokuva</th>
                      <th class="rating-cell" data-critic-id="1">
                          <div class="critic-name">Susanna Bono</div>
                          <div class="critic-media">EPISODI</div>
                          <div class="critic-bottom-row"><span class="review-count">🎬 80</span></div>
                      </th>
                      <th class="rating-cell" data-critic-id="2">
                          <div class="critic-name">Toinen Kriitikko</div>
                          <div class="critic-media">HS</div>
                          <div class="critic-bottom-row"><span class="review-count">🎬 8</span></div>
                      </th>
                  </tr>
              </thead>
              <tbody>
              </tbody>
          </table>
      </div>
      <div class="mobile-cards"></div>
      <button class="filter-publication media-filter-btn" data-publication="HS">Helsingin Sanomat</button>
      <div><button id="load-more-button">Lataa lisää</button></div>
    </div>
  `;

  let dom;
  beforeEach(() => {
    dom = setupDOM(createTestHTML(buildReviews()));
    const { document, window: win } = dom;
    win.currentMovieOffset = 0;
    document.querySelector('tbody').innerHTML = '';
    document.querySelector('.mobile-cards').innerHTML = '';
    win.loadMoreMovies(); // Lataa 30 elokuvaa (Toinen Kriitikko: 3 arviota [0, 10, 20])
  });

  it('immediately shows skeleton placeholder when clicking on a critic needing more lines', () => {
    const { document, window: win } = dom;

    let placeholderShownCount = 0;
    const origShow = win.showSkeletonPlaceholders;
    win.showSkeletonPlaceholders = (count, criticId) => {
      placeholderShownCount = count;
      origShow(count, criticId);
    };

    // Toinen Kriitikko has 8 reviews total; currently only 3 rendered (Film 0, 10, 20).
    // Target is min(8, 10) = 8. Missing = 8 - 3 = 5.
    win.filterByCritic('2');

    expect(placeholderShownCount).toBe(5);
    // After topUpSliderResults finishes loading, placeholders are cleaned up
    expect(document.querySelectorAll('.skeleton-row').length).toBe(0);
    expect(document.querySelectorAll('.skeleton-card').length).toBe(0);

    // All 8 matching reviews should now be rendered and visible
    const visibleCards = [...document.querySelectorAll('.movie-card')].filter(c => c.style.display !== 'none');
    expect(visibleCards.length).toBe(8);
  });

  it('renders spinner and skeleton elements during showSkeletonPlaceholders call', () => {
    const { document, window: win } = dom;
    win.showSkeletonPlaceholders(3, '2');

    const mobileSkeletons = document.querySelectorAll('.movie-card.skeleton-card');
    expect(mobileSkeletons.length).toBe(3);
    expect(mobileSkeletons[0].querySelector('.skeleton-spinner')).not.toBeNull();

    win.removeSkeletonPlaceholders();
    expect(document.querySelectorAll('.movie-card.skeleton-card').length).toBe(0);
  });

  it('cleans up placeholders when toggling critic filter off', () => {
    const { document, window: win } = dom;
    win.showSkeletonPlaceholders(4, '2');
    expect(document.querySelectorAll('.movie-card.skeleton-card').length).toBe(4);

    win.filterByCritic('2'); // turns on
    win.filterByCritic('2'); // turns off

    expect(document.querySelectorAll('.movie-card.skeleton-card').length).toBe(0);
    expect(document.querySelectorAll('.skeleton-row').length).toBe(0);
  });

  it('reuses cached reviews data from window._cachedReviewsData', async () => {
    const { window: win } = dom;
    expect(win._cachedReviewsData).toBeDefined();
    const data = await win.fetchReviewsJson();
    expect(data).toBe(win._cachedReviewsData);
  });
});
