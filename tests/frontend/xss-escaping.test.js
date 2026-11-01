import { describe, it, expect } from 'vitest';
import { setupDOM } from './test-helper';

// Sentinel: skreipattu data (otsikot, arvostelutekstit, URL:t) on
// luokiteltava epäluotetuksi - se ei saa päätyä HTML:ään escaappaamatta.

function buildDomWithPayload(payloadTitle, payloadReview) {
  const reviewsData = {};
  reviewsData[payloadTitle] = { 'Kriitikko 1': [payloadReview] };
  const customHTML = `
    <meta name="version" content="test">
    <script id="all-reviews-data" type="application/json">${JSON.stringify(reviewsData)}</script>
    <script id="movie-meta-data" type="application/json">${JSON.stringify({
      poster_urls: { [payloadTitle]: 'https://image.tmdb.org/p.jpg' },
      movie_review_counts: { [payloadTitle]: 1 },
      movie_rating_distributions: { [payloadTitle]: [0, 0, 0, 1, 0] }
    })}</script>
    <div class="container">
      <div class="desktop-filters">
          <input type="range" id="min-reviews-slider" min="1" max="5" value="1">
          <span id="min-reviews-value">1</span>
          <input type="range" id="star-filter-slider" min="1" max="5" value="1">
          <span id="star-filter-value">Vähintään ★</span>
          <div id="reset-filters-desktop" style="display:none"></div>
      </div>
      <div id="review-container-desktop">
          <table>
              <thead><tr class="critic-row">
                  <th class="movie-col">Elokuva</th>
                  <th class="rating-cell" data-critic-id="1">
                      <div class="critic-name">Kriitikko 1</div>
                      <div class="critic-media">HS</div>
                  </th>
              </tr></thead>
              <tbody></tbody>
          </table>
      </div>
      <div class="mobile-cards"></div>
      <div><button id="load-more-button">Lataa lisää</button></div>
  </div>`;
  window.currentMovieOffset = 0; // testissä kaikki renderöidään client-puolella
  return setupDOM(customHTML);
}

describe('XSS-escaappaus renderöitäessä', () => {
  it('HTML:ta sisältävä elokuvan nimi renderöityy tekstinä, ei markuppina', () => {
    const evil = 'Bugonia"><img src=x onerror=alert(1)>';
    const { document } = buildDomWithPayload(evil, {
      movie_title: evil, critic_name: 'Kriitikko 1', rating_stars: 4,
      source_publication: 'hs', source_url: 'https://example.com/r1'
    });
    const cards = document.querySelectorAll('.mobile-cards .movie-card');
    expect(cards.length).toBe(1);
    expect(document.querySelector('.mobile-cards img[src="x"]')).toBeNull();
    expect(cards[0].querySelector('.movie-card-title').textContent).toBe(evil);
  });

  it('review_text ei riko title-attribuuttia', () => {
    const reviewText = 'x" onmouseover="alert(1)';
    const { document } = buildDomWithPayload('Testielokuva', {
      movie_title: 'Testielokuva', critic_name: 'Kriitikko 1', rating_stars: 4,
      source_publication: 'hs', source_url: 'https://example.com/r1',
      review_text: reviewText
    });
    const pill = document.querySelector('.mobile-cards .rating-link');
    expect(pill).toBeTruthy();
    // Attribuutti ei katkea: payload pysyy title-arvon sisällä merkkijonona
    expect(pill.getAttribute('onmouseover')).toBeNull();
    expect(pill.getAttribute('title')).toBe('hs: ' + reviewText + '...');
    // Lähde-HTML:ssä lainausmerkki on escaapattu
    expect(document.querySelector('.mobile-cards').innerHTML).toContain('x&quot; onmouseover=&quot;');
  });

  it('javascript:-URL ei päädy href-attribuuttiin', () => {
    const { document } = buildDomWithPayload('Testielokuva', {
      movie_title: 'Testielokuva', critic_name: 'Kriitikko 1', rating_stars: 4,
      source_publication: 'hs', source_url: 'javascript:alert(1)'
    });
    expect(document.querySelector('.mobile-cards a.rating-link')).toBeNull();
    expect(document.querySelector('.mobile-cards span.rating-pill')).toBeTruthy();
  });
});
