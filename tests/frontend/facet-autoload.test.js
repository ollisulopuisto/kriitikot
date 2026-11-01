import { describe, it, expect, beforeEach } from 'vitest';
import { setupDOM } from './test-helper';

// Käyttäjän bugiraportti 2026-11-01: kriitikon klikkaus (esim. "9 arvostelua")
// näytti vain jo ladatut elokuvat eikä lataillut lisää, ja "Lataa lisää"
// latasi seuraavan raakaerän elokuvia faseteista välittämättä.

describe('Facet-aware auto-loading and Load more', () => {
  // 125 elokuvaa; kohdekriitikko arvostelee joka 10. elokuvan (13 arvostelua),
  // muut arvostelevat kaikki.
  const buildReviews = () => Object.fromEntries(Array.from({ length: 125 }, (_, i) => ['Film ' + i, {
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
      <button class="filter-publication media-filter-btn" data-publication="HS">Helsingin Sanomat</button>
      <div><button id="load-more-button">Lataa lisää</button></div>
    </div>
  `;

  const visibleCards = (document) => [...document.querySelectorAll('.movie-card')].filter(c => c.style.display !== 'none');
  const visibleReviewItems = (document) => [...document.querySelectorAll('.movie-card')]
    .filter(c => c.style.display !== 'none')
    .flatMap(c => [...c.querySelectorAll('.review-item')].filter(i => i.style.display !== 'none'));

  let dom;
  beforeEach(() => {
    dom = setupDOM(createTestHTML(buildReviews()));
    // Aseta lataustila kuin käyttäjä olisi lataillut yhden erän (30 + 30)
    const { document, window: win } = dom;
    win.currentMovieOffset = 0;
    document.querySelector('tbody').innerHTML = '';
    document.querySelector('.mobile-cards').innerHTML = '';
    win.loadMoreMovies(); win.loadMoreMovies();
  });

  it('auto-loads matching reviews when a critic facet is clicked', () => {
    const { document, window: win } = dom;
    // Ennen fasettia: kohdekriitikön 13 arvostelusta vain 3 on ladattu (0,10,20... -> 0,10,20 <= 60)
    win.filterByCritic('2');
    const visible = visibleReviewItems(document);
    // Tasan yksi erä: 10 osuvaa arvostelua näkyvissä, loput 2 eräpiilotettuna
    expect(visible.length).toBe(10);
    expect(visible.every(i => i.dataset.critic === '2')).toBe(true);
    expect(visibleCards(document).length).toBe(visible.length); // 1 arvostelu/elokuva
    // Lataamaan jää vielä dataa, koska arvosteluja on 13
    expect(document.getElementById('load-more-button').parentElement.style.display).toBe('block');
  });

  it('facet-aware Load more fetches the next batch of 10 matching reviews and hides at the end', () => {
    const { document, window: win } = dom;
    win.filterByCritic('2');
    const firstBatch = visibleReviewItems(document).length;
    expect(firstBatch).toBe(10);

    document.getElementById('load-more-button').click();
    const all = visibleReviewItems(document);
    // Kaikki 13 osumaa näkyvissä (loppuerä voi olla pienempi kuin 10)
    expect(all.length).toBe(13);
    expect(all.every(i => i.dataset.critic === '2')).toBe(true);
    // Ei enää osumia loppudatassa -> nappi piiloon
    expect(document.getElementById('load-more-button').parentElement.style.display).toBe('none');
  });

  it('restores the previous unfiltered window when the critic facet is toggled off', () => {
    const { document, window: win } = dom;
    const before = visibleCards(document).length; // 60
    win.filterByCritic('2');
    expect(win.currentMovieOffset).toBeGreaterThan(60);
    win.filterByCritic('2'); // pois päältä
    expect(win.currentMovieOffset).toBe(60);
    expect(visibleCards(document).length).toBe(before);
  });

  it('publication facet matches reviews whose JSON carries the full publication name', () => {
    const { document, window: win } = dom;
    // Klikkaus käyttää todellista listeneriä (nappi on templaatissa ennen init-bindingia)
    document.querySelector('.filter-publication[data-publication="HS"]').click();
    const visible = visibleReviewItems(document);
    // HS-osumia yhteensä 13 (source_publication on koko nimi "Helsingin Sanomat"),
    // joista ensimmäinen erä on tasan 10
    expect(visible.length).toBe(10);
    expect(visibleCards(document).length).toBe(10);
  });

  it('hides Load more under a facet when the remaining data has no matches', () => {
    const { document, window: win } = dom;
    // Suodata kriitikolla ja lataa kaikki osumat
    win.filterByCritic('2');
    document.getElementById('load-more-button').click();
    expect(win.tailHasFacetMatches()).toBe(false);
    expect(document.getElementById('load-more-button').parentElement.style.display).toBe('none');
  });

  it('keeps movie rows whole at batch boundaries when a movie has several matching reviews', () => {
    // Kolme HS-kriitikkoa arvostelee samat elokuvat (joka 7.): 3 osumaa/elokuva.
    // Eräraja 10 voi ylittyä vain viimeisen elokuvan omilla osumilla.
    const reviews = Object.fromEntries(Array.from({ length: 50 }, (_, i) => ['Film ' + i, {
      'Susanna Bono': [{ rating_stars: 4, source_publication: 'Episodi' }],
      ...(i % 7 === 0 ? {
        'HS A': [{ rating_stars: 5, source_publication: 'Helsingin Sanomat' }],
        'HS B': [{ rating_stars: 4, source_publication: 'Helsingin Sanomat' }],
        'HS C': [{ rating_stars: 3, source_publication: 'Helsingin Sanomat' }]
      } : {})
    }]));
    const html = createTestHTML(reviews)
      .replace('</tr>', `
        <th class="rating-cell" data-critic-id="3"><div class="critic-name">HS A</div><div class="critic-media">HS</div></th>
        <th class="rating-cell" data-critic-id="4"><div class="critic-name">HS B</div><div class="critic-media">HS</div></th>
        <th class="rating-cell" data-critic-id="5"><div class="critic-name">HS C</div><div class="critic-media">HS</div></th>
      </tr>`);
    const { document, window: win } = setupDOM(html);
    win.currentMovieOffset = 0;
    document.querySelector('tbody').innerHTML = '';
    document.querySelector('.mobile-cards').innerHTML = '';
    win.loadMoreMovies(); // 30 elokuvaa: osumat 0,7,14,21,28 (5 x 3 = 15)
    document.querySelector('.filter-publication[data-publication="HS"]').click();

    const pairSet = () => new Set(visibleReviewItems(document).map(i => i.closest('.movie-card').dataset.movie + '|' + i.dataset.critic));
    // Erä 1: 4 elokuvaa (3+3+3+3=12 osumaa); raja ylittyy koska 9 < 10 ja 4. elokuva viedään kokonaan
    expect(visibleCards(document).length).toBe(4);
    expect(visibleReviewItems(document).length).toBe(12);
    expect(pairSet().size).toBe(12); // ei duplikaatteja
    expect(document.getElementById('load-more-button').parentElement.style.display).toBe('block');

    // Erä 2: +10 -> paljastus 20; elokuvat 5-7 paljastuvat (12+3+3+3=21), 8. jää piiloon
    document.getElementById('load-more-button').click();
    expect(visibleCards(document).length).toBe(7);
    expect(visibleReviewItems(document).length).toBe(21);
    expect(pairSet().size).toBe(21); // ei duplikaatteja erien välillä
    expect(document.getElementById('load-more-button').parentElement.style.display).toBe('block');

    // Erä 3: loput 3 osumaa; nappi piiloutuu
    document.getElementById('load-more-button').click();
    expect(visibleCards(document).length).toBe(8);
    expect(visibleReviewItems(document).length).toBe(24);
    expect(pairSet().size).toBe(24); // kaikki osumat, ei kaksoiskappaleita
    expect(document.getElementById('load-more-button').parentElement.style.display).toBe('none');
  });

  it('star facet combined with critic facet narrows matching reviews', () => {
    const { document, window: win } = dom;
    win.filterByCritic('1'); // Susanna Bono: 4 stars, joka elokuvassa
    const visible = visibleReviewItems(document);
    expect(visible.length).toBeGreaterThanOrEqual(10);
    expect(visible.every(i => i.dataset.critic === '1')).toBe(true);
    // Tähtiraja 5: Susannan 4-tähden arvostelut eivät täsmää
    document.getElementById('star-filter-slider').value = '5';
    win.filterByStars(5);
    win.topUpSliderResults();
    expect(visibleReviewItems(document).length).toBe(0);
    expect(document.getElementById('load-more-button').parentElement.style.display).toBe('none');
  });
});
