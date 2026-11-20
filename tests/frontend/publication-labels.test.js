import { it, expect } from 'vitest';
import { setupDOM, minimalHTML } from './test-helper';

it('keeps full publication names on lazy-loaded mobile labels', () => {
  window.innerWidth = 390;
  const reviews = {'Test film': {'Susanna Bono': [{
    rating_stars: 3, source_publication: 'IS', publication_short: 'is',
    source_url: 'https://example.test/review', review_text: 'A review',
  }]}};
  const html = minimalHTML.replace('<div class="container">', `<div class="container">
    <script id="publication-names-data" type="application/json">{"IS":"Ilta-Sanomat"}</script>
    <script id="all-reviews-data" type="application/json">${JSON.stringify(reviews)}</script>
    <script id="movie-meta-data" type="application/json">{}</script>
    <button id="load-more-button">Lataa lisää</button>`);
  const { window: win, document } = setupDOM(html);
  document.querySelector('.mobile-cards').innerHTML = '';
  win.currentMovieOffset = 0;
  win.loadMoreMovies();
  const label = document.querySelector('.review-media');
  expect(label.textContent).toBe('IS');
  expect(label.title).toBe('Ilta-Sanomat');
  expect(label.getAttribute('aria-label')).toBe('Ilta-Sanomat');
});
