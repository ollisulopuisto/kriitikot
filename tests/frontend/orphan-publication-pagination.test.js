import { it, expect } from 'vitest';
import { setupDOM, minimalHTML } from './test-helper';

it.each([390, 1400])('loads past an orphan-publication review at width %i', (width) => {
  window.innerWidth = width;
  const reviews = Object.fromEntries(Array.from({ length: 65 }, (_, i) => [`Film ${i}`, {
    'Susanna Bono': [{
      rating_stars: 4, source_publication: i === 30 ? null : 'Episodi',
      publication_short: i === 30 ? null : 'episodi',
      source_url: `https://example.test/${i}`, review_text: 'Fixture review',
    }],
  }]));
  const html = minimalHTML.replace('<div class="container">', `<div class="container">
    <script id="all-reviews-data" type="application/json">${JSON.stringify(reviews)}</script>
    <script id="movie-meta-data" type="application/json">{}</script>
    <div><button id="load-more-button">Lataa lisää</button></div>`);
  const { window: win, document } = setupDOM(html);
  document.querySelector('tbody').innerHTML = '';
  document.querySelector('.mobile-cards').innerHTML = '';
  win.currentMovieOffset = 0;
  win.loadMoreMovies();
  expect(win.currentMovieOffset).toBe(30);
  expect(() => win.loadMoreMovies()).not.toThrow();
  expect(win.currentMovieOffset).toBe(60);
  const orphan = [...document.querySelectorAll('.movie-card')]
    .find(card => card.textContent.includes('Film 30'));
  expect(orphan).toBeDefined();
  expect(orphan.querySelector('.review-media').textContent).toBe('');
  const button = document.getElementById('load-more-button');
  expect(button.disabled).toBe(false);
  expect(button.textContent).toBe('Lataa lisää');
  win.loadMoreMovies();
  expect(win.currentMovieOffset).toBe(65);
  expect(document.querySelectorAll('.movie-card')).toHaveLength(65);
  expect(button.disabled).toBe(false);
});
