import { describe, it, expect, beforeEach } from 'vitest';
import { setupDOM } from './test-helper';

/**
 * Sarakkeet järjestetään latauksessa niin että ylimpien elokuvien arvostelijat
 * tulevat vasemmalle. Se tapahtuu VASTA app.js:n DOMContentLoaded-käsittelijän
 * jälkeen, joten siihen mennessä talletettu kriitikkojärjestys vanhenee.
 *
 * Regressio: kun arvosteludata siirtyi inline-JSONista asynkroniseen
 * reviews.json-hakuun, "Lataa lisää" alkoi renderöidä rivit vanhentuneessa
 * järjestyksessä. Solut osuivat väärien otsikoiden alle, ja koska
 * sarakkeiden näkyvyyslogiikka lukee juuri noita soluja, se piilotti vääriä
 * sarakkeita — ylimmän elokuvan arviot katosivat näkyvistä.
 */

describe('Kriitikkosarakkeiden järjestys', () => {
  beforeEach(() => {
    window.innerWidth = 1400;
  });

  it('lukee järjestyksen otsikoista, ei muistista', () => {
    const { window: win, document } = setupDOM(`
      <div id="review-container-desktop">
        <table>
          <thead>
            <tr class="critic-row">
              <th class="movie-col">Elokuva</th>
              <th class="rating-cell" data-critic-id="7"><div class="critic-name">Zeta</div></th>
              <th class="rating-cell" data-critic-id="3"><div class="critic-name">Alfa</div></th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <div class="mobile-cards"></div>
    `);

    expect(typeof win.syncCriticOrderFromDom).toBe('function');
    win.syncCriticOrderFromDom();

    // Järjestyksen on vastattava DOMia, ei aakkosia
    const names = [...document.querySelectorAll('thead th.rating-cell .critic-name')]
      .map((n) => n.textContent);
    expect(names).toEqual(['Zeta', 'Alfa']);
  });

  it('päivittää järjestyksen kun sarakkeet järjestetään uudelleen', () => {
    const { window: win, document } = setupDOM(`
      <div id="review-container-desktop">
        <table>
          <thead>
            <tr class="critic-row">
              <th class="movie-col">Elokuva</th>
              <th class="rating-cell" data-critic-id="1"><div class="critic-name">Ensin</div></th>
              <th class="rating-cell" data-critic-id="2"><div class="critic-name">Toinen</div></th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <div class="mobile-cards"></div>
    `);

    const row = document.querySelector('thead tr.critic-row');
    const headers = [...row.querySelectorAll('th.rating-cell')];

    // Simuloi sarakkeiden uudelleenjärjestystä
    row.appendChild(headers[0]);
    document.dispatchEvent(new win.CustomEvent('table-sorted'));

    const names = [...document.querySelectorAll('thead th.rating-cell .critic-name')]
      .map((n) => n.textContent);
    expect(names).toEqual(['Toinen', 'Ensin']);
  });

  it('renderöi uudet rivit otsikoiden nykyisessä järjestyksessä', () => {
    const reviewsData = {};
    for (let i = 1; i <= 31; i += 1) {
      reviewsData[`Elokuva ${i}`] = {
        Beeta: [{
          movie_title: `Elokuva ${i}`, critic_name: 'Beeta', rating_stars: 5,
          source_publication: 'hs', source_url: `https://example.com/${i}`
        }]
      };
    }

    const { document } = setupDOM(`
      <meta name="version" content="test">
      <script id="all-reviews-data" type="application/json">${JSON.stringify(reviewsData)}</script>
      <script id="movie-meta-data" type="application/json">{}</script>
      <div id="review-container-desktop">
        <table>
          <thead>
            <tr class="critic-row">
              <th class="movie-col">Elokuva</th>
              <th class="rating-cell" data-critic-id="1"><div class="critic-name">Alfa</div></th>
              <th class="rating-cell" data-critic-id="2"><div class="critic-name">Beeta</div></th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <div class="mobile-cards"></div>
      <div><button id="load-more-button">Lataa lisää</button></div>
    `);

    const rows = [...document.querySelectorAll('#review-container-desktop tbody tr')];
    expect(rows.length).toBeGreaterThan(0);

    // Beeta on toinen sarake, joten arvion on oltava toisessa arvosolussa
    const headerNames = [...document.querySelectorAll('thead th.rating-cell .critic-name')]
      .map((n) => n.textContent);
    const beetaIndex = headerNames.indexOf('Beeta');

    rows.forEach((row) => {
      const cells = [...row.querySelectorAll('td.rating-cell')];
      const withReview = cells.findIndex((c) => c.querySelector('.rating-pill'));
      expect(withReview).toBe(beetaIndex);
    });
  });
});
