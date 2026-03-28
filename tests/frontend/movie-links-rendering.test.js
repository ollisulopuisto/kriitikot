import { describe, it, expect } from 'vitest';
import { setupDOM } from './test-helper';

function buildReviewsData() {
  const data = {};
  for (let i = 1; i <= 31; i += 1) {
    data[`Elokuva ${i}`] = {
      'Kriitikko 1': [
        {
          movie_title: `Elokuva ${i}`,
          critic_name: 'Kriitikko 1',
          rating_stars: 4,
          source_publication: 'hs',
          source_url: `https://example.com/review-${i}`
        }
      ]
    };
  }
  return data;
}

describe('Letterboxd- ja Nytleffaan-linkit renderöityvät oikein', () => {
  it('renderöi dynaamisesti ladattuun desktop- ja mobile-näkymään oikeat linkit sekä sparkline-jakauman', () => {
    const reviewsData = buildReviewsData();
    const targetMovie = 'Elokuva 31';
    const letterboxdUrl = 'https://letterboxd.com/film/elokuva-31-2026/';
    const nytleffaanUrl = 'https://www.nytleffaan.fi/elokuva/elokuva312026/';

    const movieMetaData = {
      nytleffaan_urls: { [targetMovie]: nytleffaanUrl },
      letterboxd_urls: { [targetMovie]: letterboxdUrl },
      poster_urls: {},
      movie_review_counts: { [targetMovie]: 1 },
      movie_rating_distributions: { [targetMovie]: [0, 1, 3, 2, 0] }
    };

    const customHTML = `
      <meta name="version" content="test">
      <script id="all-reviews-data" type="application/json">${JSON.stringify(reviewsData)}</script>
      <script id="movie-meta-data" type="application/json">${JSON.stringify(movieMetaData)}</script>
      <div class="container">
        <div class="desktop-filters">
            <input type="range" id="min-reviews-slider" min="1" max="5" value="1">
            <span id="min-reviews-value">1</span>
            <input type="range" id="star-filter-slider" min="1" max="5" value="1">
            <span id="star-filter-value">Vähintään ★</span>
            <div id="reset-filters-desktop" style="display:none"></div>
        </div>
        <button class="media-filter-btn" data-publication="HS">HS</button>
        <div id="review-container-desktop">
            <table>
                <thead>
                    <tr class="critic-row">
                        <th class="movie-col">Elokuva</th>
                        <th class="rating-cell" data-critic-id="1">
                            <div class="critic-name">Kriitikko 1</div>
                            <div class="critic-media">HS</div>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr data-review-count="1">
                        <td class="movie-col" data-poster="" data-letterboxd="" data-nytleffaan="">
                            <div class="movie-title-main">Elokuva 1</div>
                            <div class="movie-review-count">🎬 1</div>
                        </td>
                        <td class="rating-cell"><span class="rating-pill"><span class="rating-stars">★★★★</span></span></td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="mobile-cards"></div>
        <div><button id="load-more-button">Lataa lisää</button></div>
      </div>
    `;

    const { document } = setupDOM(customHTML);

    const desktopMovieCell = Array.from(document.querySelectorAll('#review-container-desktop tbody .movie-col'))
      .find((cell) => cell.querySelector('.movie-title-main')?.textContent === targetMovie);

    expect(desktopMovieCell).toBeTruthy();
    const desktopLinks = desktopMovieCell.querySelectorAll('.movie-meta-row .movie-link');
    expect(desktopLinks).toHaveLength(2);
    expect(desktopLinks[0].textContent.trim()).toBe('Osta liput');
    expect(desktopLinks[0].getAttribute('href')).toBe(nytleffaanUrl);
    expect(desktopLinks[0].getAttribute('rel')).toBe('noopener noreferrer');
    expect(desktopLinks[1].textContent.trim()).toBe('Letterboxd');
    expect(desktopLinks[1].getAttribute('href')).toBe(letterboxdUrl);
    expect(desktopLinks[1].getAttribute('rel')).toBe('noopener noreferrer');
    expect(desktopMovieCell.querySelectorAll('.movie-sparkline .spark-bar')).toHaveLength(5);

    const mobileCard = document.querySelector(`.mobile-cards .movie-card[data-movie="${targetMovie}"]`);
    expect(mobileCard).toBeTruthy();
    const mobileLinks = mobileCard.querySelectorAll('.movie-card-links .movie-link');
    expect(mobileLinks).toHaveLength(2);
    expect(mobileLinks[0].textContent.trim()).toBe('Osta liput');
    expect(mobileLinks[0].getAttribute('href')).toBe(nytleffaanUrl);
    expect(mobileLinks[0].getAttribute('rel')).toBe('noopener noreferrer');
    expect(mobileLinks[1].textContent.trim()).toBe('Letterboxd');
    expect(mobileLinks[1].getAttribute('href')).toBe(letterboxdUrl);
    expect(mobileLinks[1].getAttribute('rel')).toBe('noopener noreferrer');
    expect(mobileCard.querySelectorAll('.movie-card-sparkline .spark-bar')).toHaveLength(5);
  });
});
