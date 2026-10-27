import { describe, it, expect, beforeEach } from 'vitest';
import { setupDOM } from './test-helper';

describe('Facet reapplication when pressing Load more', () => {
  let dom;

  const mockReviews = {
    'Movie 1': {
      'Susanna Bono': [{ rating_stars: 5, source_publication: 'episodi' }]
    },
    'Movie 2': {
      'Toinen Kriitikko': [{ rating_stars: 2, source_publication: 'hs' }]
    },
    'Movie 3': {
      'Susanna Bono': [{ rating_stars: 4, source_publication: 'episodi' }],
      'Toinen Kriitikko': [{ rating_stars: 4, source_publication: 'hs' }]
    },
    'Movie 4': {
      'Toinen Kriitikko': [{ rating_stars: 1, source_publication: 'hs' }]
    }
  };

  const createTestHTML = (reviewsData = mockReviews) => `
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
                          <div class="critic-media">Episodi</div>
                      </th>
                      <th class="rating-cell" data-critic-id="2">
                          <div class="critic-name">Toinen Kriitikko</div>
                          <div class="critic-media">HS</div>
                      </th>
                  </tr>
              </thead>
              <tbody>
              </tbody>
          </table>
      </div>
      <div class="mobile-cards"></div>
      <div><button id="load-more-button">Lataa lisää</button></div>
    </div>
  `;

  beforeEach(() => {
    window.innerWidth = 1400;
    dom = setupDOM(createTestHTML());
    const { window: win } = dom;

    win.innerWidth = 1400;
    if (typeof win.ensureDesktopTable === 'function') {
      win.ensureDesktopTable();
    }
  });

  it('reapplies minimum stars filter on Load More', () => {
    const { document, window: win } = dom;

    // Activate star filter: 4 stars
    const starSlider = document.getElementById('star-filter-slider');
    if (starSlider) {
      starSlider.value = 4;
    }
    win.filterByStars(4);

    // Reset currentMovieOffset to test loadMoreMovies explicitly
    win.currentMovieOffset = 0;
    // Clear tbody to simulate fresh load
    const tbody = document.querySelector('#review-container-desktop tbody');
    tbody.innerHTML = '';
    const mobileContainer = document.querySelector('.mobile-cards');
    mobileContainer.innerHTML = '';

    win.loadMoreMovies();

    // Movie 1 (5 stars) -> visible
    // Movie 2 (2 stars) -> hidden
    // Movie 3 (4 stars) -> visible
    // Movie 4 (1 star) -> hidden

    const desktopRows = Array.from(document.querySelectorAll('#review-container-desktop tbody tr'));

    const visibleDesktopTitles = desktopRows
      .filter(r => r.style.display !== 'none')
      .map(r => r.querySelector('.movie-title-main').textContent.trim());

    const hiddenDesktopTitles = desktopRows
      .filter(r => r.style.display === 'none')
      .map(r => r.querySelector('.movie-title-main').textContent.trim());

    expect(visibleDesktopTitles).toContain('Movie 1');
    expect(visibleDesktopTitles).toContain('Movie 3');
    expect(hiddenDesktopTitles).toContain('Movie 2');
    expect(hiddenDesktopTitles).toContain('Movie 4');

    const mobileCards = Array.from(document.querySelectorAll('.mobile-cards .movie-card'));
    const visibleMobileTitles = mobileCards
      .filter(c => c.style.display !== 'none')
      .map(c => c.querySelector('.movie-card-title').textContent.trim());

    expect(visibleMobileTitles).toContain('Movie 1');
    expect(visibleMobileTitles).toContain('Movie 3');
  });

  it('reapplies minimum review count filter on Load More', () => {
    const { document, window: win } = dom;

    // Activate min reviews filter: 2 reviews (mapped value 2)
    const reviewSlider = document.getElementById('min-reviews-slider');
    if (reviewSlider) {
      reviewSlider.value = 2; // mapped to 2 reviews
    }
    win.filterByReviewCount(2);

    win.currentMovieOffset = 0;
    document.querySelector('#review-container-desktop tbody').innerHTML = '';
    document.querySelector('.mobile-cards').innerHTML = '';

    win.loadMoreMovies();

    // Movie 1 has 1 review -> hidden
    // Movie 2 has 1 review -> hidden
    // Movie 3 has 2 reviews -> visible
    // Movie 4 has 1 review -> hidden

    const desktopRows = Array.from(document.querySelectorAll('#review-container-desktop tbody tr'));

    const visibleDesktopTitles = desktopRows
      .filter(r => r.style.display !== 'none')
      .map(r => r.querySelector('.movie-title-main').textContent.trim());

    expect(visibleDesktopTitles).toEqual(['Movie 3']);
  });

  it('reapplies outlet (publication) facet on Load More', () => {
    const { document, window: win } = dom;

    // Create publication filter button in DOM
    const pubBtn = document.createElement('button');
    pubBtn.className = 'filter-publication active';
    pubBtn.dataset.publication = 'hs';
    document.body.appendChild(pubBtn);

    win.applyPublicationFilter(['hs']);

    win.currentMovieOffset = 0;
    document.querySelector('#review-container-desktop tbody').innerHTML = '';
    document.querySelector('.mobile-cards').innerHTML = '';

    win.loadMoreMovies();

    // Movie 1 has Episodi review -> hidden
    // Movie 2 has HS review -> visible
    // Movie 3 has Episodi + HS review -> visible
    // Movie 4 has HS review -> visible

    const desktopRows = Array.from(document.querySelectorAll('#review-container-desktop tbody tr'));

    const visibleDesktopTitles = desktopRows
      .filter(r => r.style.display !== 'none')
      .map(r => r.querySelector('.movie-title-main').textContent.trim());

    const hiddenDesktopTitles = desktopRows
      .filter(r => r.style.display === 'none')
      .map(r => r.querySelector('.movie-title-main').textContent.trim());

    expect(visibleDesktopTitles).toContain('Movie 2');
    expect(visibleDesktopTitles).toContain('Movie 3');
    expect(visibleDesktopTitles).toContain('Movie 4');
    expect(hiddenDesktopTitles).toContain('Movie 1');
  });
});
