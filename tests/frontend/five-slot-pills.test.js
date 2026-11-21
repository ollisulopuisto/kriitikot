import {describe, it, expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {setupDOM} from './test-helper';
const app = readFileSync('static/app.js','utf8');
const helpers = app.slice(app.indexOf('function escapeHtml('), app.indexOf('// Desktop-taulukon'));
const create = app.slice(app.indexOf('function createReviewPill('), app.indexOf('/**\n * Renderöi elokuvarivin', app.indexOf('function createReviewPill(')));
const render = new Function('review', `const allPublicationMap={};${helpers}${create};return createReviewPill(review);`);
describe('five fixed rating slots',()=>{
 it('keeps proportional sizes and glow on the glyphs in both published stylesheets',()=>{
  const css=readFileSync('static/css/table.css','utf8');
  expect(css).toBe(readFileSync('docs/static/css/table.css','utf8'));
  expect(css).not.toMatch(/scaleX\(/);
  for(const size of [18,20,22,24,25])
   expect(css).toContain(`--cluster-size: ${size}px;`);
  expect(css).toContain('.rating-star-empty { display: none; }');
  expect(css).toContain('.rating-pill:hover { transform: none; }');
  expect(css).toContain('.rating-pill.stars-5 .rating-star {');
  expect(css).toContain('--cluster-color: #179447;');
 });
 for(let rating=1;rating<=5;rating++) for(const url of ['https://example.com/review','']) {
  it(`renders ${rating}/5 with ${url?'a link':'no link'} without changing the numeric text`,()=>{
   document.body.innerHTML=render({rating_stars:rating,source_url:url,source_publication:'hs'});
   const pill=document.querySelector('.rating-pill'),stars=pill.querySelector('.rating-stars');
   expect(stars.querySelectorAll('.rating-star')).toHaveLength(5);
   expect(stars.querySelectorAll('.rating-star-empty')).toHaveLength(5-rating);
   expect(stars.textContent).toBe('★'.repeat(rating));
   expect(stars.getAttribute('aria-label')).toBe(`${rating}/5 tähteä`);
   expect(stars.getAttribute('role')).toBe('img');
   expect([...stars.children].every(s=>s.getAttribute('aria-hidden')==='true')).toBe(true);
   expect(pill.tagName).toBe(url?'A':'SPAN');
  });
 }
 it('empty slots do not turn low reviews into five-star matches',()=>{
  window.innerWidth=1400;window.currentMovieOffset=0;
  const data={Low:{Critic:[{rating_stars:2,source_publication:'hs'}]},High:{Critic:[{rating_stars:5,source_publication:'hs'}]}};
  setupDOM(`<script id="all-reviews-data" type="application/json">${JSON.stringify(data)}</script><script id="movie-meta-data" type="application/json">{}</script><div class="desktop-filters"><input id="star-filter-slider" value="1"><input id="min-reviews-slider" value="1"><span id="min-reviews-value"></span><span id="star-filter-value"></span></div><div id="review-container-desktop"><table><thead><tr><th class="movie-col">Movie</th><th class="rating-cell" data-critic-id="1"><div class="critic-name">Critic</div><div class="critic-media">HS</div></th></tr></thead><tbody></tbody></table></div><div class="mobile-cards"></div><div><button id="load-more-button">More</button></div>`);
  window.ensureDesktopTable?.();
  // Repeated filter edits and clearing must restore both responsive trees.
  for(const threshold of [4,1,5,1,3]) {
   document.querySelector('#star-filter-slider').value=String(threshold);
   window.filterByStars(threshold);window.reconcileFacetVisibility();
   for(const selector of ['tbody tr','.movie-card']) {
    const nodes=[...document.querySelectorAll(selector)];
    expect(nodes).toHaveLength(2);
    const low=nodes.find(n=>n.textContent.includes('Low')),high=nodes.find(n=>n.textContent.includes('High'));
    expect(low.style.display==='none').toBe(threshold>2);
    expect(high.style.display).not.toBe('none');
   }
  }
 });
});
