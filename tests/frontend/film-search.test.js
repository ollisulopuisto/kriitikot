import { describe, it, expect, vi } from 'vitest';
import { setupDOM } from './test-helper';

describe('film search intersects catalog facets', () => {
  it('finds an unrendered tail title, intersects stars, and reset restores pagination', async () => {
    const reviews=Object.fromEntries(Array.from({length:105},(_,i)=>[i===104?'Äänekäs ZEBRA':'Film '+i,{'Critic':[{rating_stars:i===104?3:5,source_publication:'HS'}]}]));
    window.currentMovieOffset=30;
    const initial=Object.keys(reviews).slice(0,30).map(title=>`<div class="movie-card" data-movie="${title}" data-review-count="1"><div class="review-item" data-critic="1" data-publication="HS"><span class="rating-stars">★★★★★</span></div></div>`).join('');
    setupDOM(`<div class="container"><script id="all-reviews-data" type="application/json">${JSON.stringify(reviews)}</script>
    <input class="film-search"><input class="film-search"><input id="min-reviews-slider" value="1"><span id="min-reviews-value"></span><input id="star-filter-slider" value="1"><span id="star-filter-value"></span><button id="reset-filters-desktop"></button>
    <div id="review-container-desktop"><table><thead><tr><th class="movie-col">Film</th><th class="rating-cell" data-critic-id="1"><div class="critic-name">Critic</div><div class="critic-media">HS</div></th></tr></thead><tbody></tbody></table></div><div class="mobile-cards">${initial}</div><div><button id="load-more-button">More</button></div></div>`);
    const input=document.querySelector('.film-search');
    const columnPass = window.updateCriticColumnVisibility;
    let completedColumnPasses = 0;
    window.updateCriticColumnVisibility = (...args) => {
      if (!window.facetReapplyDepth) completedColumnPasses++;
      return columnPass(...args);
    };

    expect(document.querySelectorAll('.movie-card')).toHaveLength(60);
    input.value='ääNEKÄS';input.dispatchEvent(new Event('input',{bubbles:true}));
    await new Promise(r=>setTimeout(r,180));
    const visible=()=>[...document.querySelectorAll('.movie-card')].filter(n=>n.style.display!=='none').map(n=>n.dataset.movie);
    expect(document.querySelectorAll('.film-search')[1].value).toBe('ääNEKÄS');
    expect(visible()).toEqual(['Äänekäs ZEBRA']);
    expect(completedColumnPasses).toBeLessThanOrEqual(2);
    expect(window.facetReapplyDepth).toBe(0);
    const selected = document.querySelector('.movie-card[data-movie="Äänekäs ZEBRA"]');
    selected.dataset.filtered = 'true';
    const topUp = vi.spyOn(window, 'topUpSliderResults');
    input.value='  ÄÄNEKÄS  ';input.dispatchEvent(new Event('input',{bubbles:true}));
    await new Promise(r=>setTimeout(r,180));
    expect(topUp).not.toHaveBeenCalled();
    expect(selected.dataset.filtered).toBe('true');
    delete selected.dataset.filtered;

    expect(window.currentMovieOffset).toBe(105);
    expect(document.querySelectorAll('.movie-card')).toHaveLength(61);
    const slider=document.querySelector('#star-filter-slider');slider.value='4';window.filterByStars(4);window.reconcileFacetVisibility();
    expect(visible()).toEqual([]);
    slider.value='1';window.filterByStars(1);window.reconcileFacetVisibility();
    expect(visible()).toEqual(['Äänekäs ZEBRA']);
    window.resetAllFilters();
    expect(input.value).toBe('');
    expect(visible()).toHaveLength(60);
    expect(window.currentMovieOffset).toBe(60);
  });
});
