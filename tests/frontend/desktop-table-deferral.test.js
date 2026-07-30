import { describe, it, expect, beforeEach } from 'vitest';
import { setupDOM } from './test-helper';

/**
 * Desktop-taulukon rivit odottavat <template>-elementissä, jotta mobiilissa
 * niiden ~2500 solua ei rakenneta DOMiin lainkaan.
 */

function buildReviewsData(count = 31) {
  const data = {};
  for (let i = 1; i <= count; i += 1) {
    data[`Elokuva ${i}`] = {
      'Kriitikko 1': [{
        movie_title: `Elokuva ${i}`,
        critic_name: 'Kriitikko 1',
        rating_stars: 4,
        source_publication: 'hs',
        source_url: `https://example.com/review-${i}`
      }]
    };
  }
  return data;
}

const htmlWithTemplate = (reviewsData) => `
  <meta name="version" content="test">
  <script id="all-reviews-data" type="application/json">${JSON.stringify(reviewsData)}</script>
  <script id="movie-meta-data" type="application/json">{}</script>
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
          <template id="desktop-rows">
            <tr data-review-count="1">
              <td class="movie-col" data-poster="" data-letterboxd="" data-nytleffaan="">
                <div class="movie-title-main">Elokuva 1</div>
              </td>
              <td class="rating-cell"><span class="rating-pill"><span class="rating-stars">★★★★</span></span></td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
    <div class="mobile-cards"></div>
    <div><button id="load-more-button">Lataa lisää</button></div>
  </div>
`;

function setViewport(width) {
  window.innerWidth = width;
}

describe('Desktop-taulukon laiska rakentaminen', () => {
  beforeEach(() => {
    setViewport(1024);
  });

  it('parsii <template>-elementin tbodyn sisällä ilman että rivit ovat DOMissa', () => {
    // Mobiilileveys: templatea ei pureta
    setViewport(390);
    const { document } = setupDOM(htmlWithTemplate(buildReviewsData(1)));

    const template = document.getElementById('desktop-rows');
    expect(template).toBeTruthy();
    // Template-sisältö on olemassa mutta ei osa dokumenttia
    expect(template.content.querySelectorAll('tr').length).toBe(1);
    expect(document.querySelectorAll('#review-container-desktop tbody tr').length).toBe(0);
  });

  it('ei rakenna desktop-rivejä mobiilileveydellä edes lisälatauksen jälkeen', () => {
    setViewport(390);
    const { document } = setupDOM(htmlWithTemplate(buildReviewsData(31)));

    // Kortit renderöityvät normaalisti
    expect(document.querySelectorAll('.mobile-cards .movie-card').length).toBeGreaterThan(0);
    // Taulukko pysyy tyhjänä
    expect(document.querySelectorAll('#review-container-desktop tbody tr').length).toBe(0);
  });

  it('rakentaa desktop-rivit työpöytäleveydellä', () => {
    setViewport(1280);
    const { document } = setupDOM(htmlWithTemplate(buildReviewsData(31)));

    const rows = document.querySelectorAll('#review-container-desktop tbody tr');
    // Templaten rivi + JS:n renderöimät loput
    expect(rows.length).toBeGreaterThan(1);

    const titles = Array.from(rows)
      .map((r) => r.querySelector('.movie-title-main')?.textContent)
      .filter(Boolean);
    expect(titles).toContain('Elokuva 1');
    expect(titles).toContain('Elokuva 31');
  });

  it('täydentää rivit jälkikäteen kun näkymä levenee työpöytäkokoon', () => {
    setViewport(390);
    const { document, window: win } = setupDOM(htmlWithTemplate(buildReviewsData(31)));

    expect(document.querySelectorAll('#review-container-desktop tbody tr').length).toBe(0);

    // Simuloi tabletin kääntöä: leveys kasvaa ja taulukko aktivoidaan
    setViewport(1280);
    win.activateDesktopTable();

    const rows = document.querySelectorAll('#review-container-desktop tbody tr');
    expect(rows.length).toBeGreaterThan(1);

    const titles = Array.from(rows)
      .map((r) => r.querySelector('.movie-title-main')?.textContent)
      .filter(Boolean);
    // Sekä templaten rivi että mobiilissa ladatut elokuvat ovat mukana
    expect(titles).toContain('Elokuva 1');
    expect(titles).toContain('Elokuva 31');
    // Ei duplikaatteja
    expect(new Set(titles).size).toBe(titles.length);
  });
});
