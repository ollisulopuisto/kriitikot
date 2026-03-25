import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setupDOM } from './test-helper';

const customHTML = `
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
            <thead>
                <tr class="critic-row">
                    <th class="movie-col">Elokuva</th>
                    <th class="rating-cell" data-critic-id="1">
                        <div class="critic-name">Kriitikko 1</div>
                    </th>
                    <th class="rating-cell" data-critic-id="2">
                        <div class="critic-name">Kriitikko 2</div>
                    </th>
                    <th class="rating-cell" data-critic-id="3">
                        <div class="critic-name">Kriitikko 3</div>
                    </th>
                </tr>
            </thead>
            <tbody>
                <tr data-review-count="3">
                    <td class="movie-col">Elokuva Kaikilla</td>
                    <td class="rating-cell"><span class="rating-pill"><span class="rating-stars">★★★</span></span></td>
                    <td class="rating-cell"><span class="rating-pill"><span class="rating-stars">★★★</span></span></td>
                    <td class="rating-cell"><span class="rating-pill"><span class="rating-stars">★★★</span></span></td>
                </tr>
                <tr data-review-count="1">
                    <td class="movie-col" id="target-movie-cell">Vain Kriitikko 1</td>
                    <td class="rating-cell"><span class="rating-pill"><span class="rating-stars">★★★★★</span></span></td>
                    <td class="rating-cell"></td>
                    <td class="rating-cell"></td>
                </tr>
                <tr data-review-count="1">
                    <td class="movie-col">Vain Kriitikko 2</td>
                    <td class="rating-cell"></td>
                    <td class="rating-cell"><span class="rating-pill"><span class="rating-stars">★★★★★</span></span></td>
                    <td class="rating-cell"></td>
                </tr>
            </tbody>
        </table>
    </div>
  </div>
`;

describe('Elokuvan klikkaus ja sarakkeiden näkyvyys', () => {
  let dom;

  beforeEach(() => {
    dom = setupDOM(customHTML);
    // Initialize handlers
    if (typeof dom.window.initMovieClickHandlers === 'function') {
      dom.window.initMovieClickHandlers();
    }
  });

  it('Pitäisi piilottaa sarakkeet, joissa ei ole arviota valitulle elokuvalle', () => {
    const { document } = dom;
    
    const header1 = document.querySelector('th[data-critic-id="1"]');
    const header2 = document.querySelector('th[data-critic-id="2"]');
    const header3 = document.querySelector('th[data-critic-id="3"]');
    
    expect(header1.classList.contains('filter-hidden')).toBe(false);
    expect(header2.classList.contains('filter-hidden')).toBe(false);
    expect(header3.classList.contains('filter-hidden')).toBe(false);

    // Klikataan "Vain Kriitikko 1"
    const movieCell = document.getElementById('target-movie-cell');
    movieCell.click();

    // TARKISTUS: Kriitikko 1 pitäisi olla näkyvissä, 2 ja 3 piilossa
    expect(header1.classList.contains('filter-hidden')).toBe(false);
    expect(header2.classList.contains('filter-hidden')).toBe(true);
    expect(header3.classList.contains('filter-hidden')).toBe(true);
    
    // Tarkistetaan myös display: none
    expect(header1.style.display).not.toBe('none');
    expect(header2.style.display).toBe('none');
    expect(header3.style.display).toBe('none');
  });
});
