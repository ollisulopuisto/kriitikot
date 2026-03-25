import { fs } from 'vitest';
import * as path from 'path';
import { readFileSync } from 'fs';

export function setupDOM(html) {
  document.documentElement.innerHTML = html;

  // Lataa koodit JSDOM-ympäristöön
  const loadScript = (filename) => {
    const filePath = path.resolve(process.cwd(), 'static', filename);
    const code = readFileSync(filePath, 'utf8');
    
    // Suoritetaan koodi globaalissa kontekstissa
    try {
      const fn = new Function('window', 'document', 'console', code);
      fn(window, document, console);
    } catch (e) {
      console.error(`Error loading script ${filename}:`, e);
    }
  };

  loadScript('app.js');
  loadScript('filters.js');
  loadScript('interactions.js');
  loadScript('ui.js');

  // Trigger initialization
  document.dispatchEvent(new Event('DOMContentLoaded'));

  return {
    window,
    document
  };
}

export const minimalHTML = `
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
                        <div class="critic-name">Susanna Bono</div>
                        <div class="critic-media">Episodi</div>
                    </th>
                    <th class="rating-cell" data-critic-id="2">
                        <div class="critic-name">Toinen Kriitikko</div>
                        <div class="critic-media">HS</div>
                    </th>
                </tr>
            </thead>
            <tbody>
                <tr data-review-count="1">
                    <td class="movie-col">Huippu Elokuva</td>
                    <td class="rating-cell">
                        <span class="rating-pill"><span class="rating-stars">★★★★★</span></span>
                    </td>
                    <td class="rating-cell">
                        <span class="rating-pill"><span class="rating-stars">★★</span></span>
                    </td>
                </tr>
                <tr data-review-count="1">
                    <td class="movie-col">Huono Elokuva</td>
                    <td class="rating-cell">
                        <span class="rating-pill"><span class="rating-stars">★</span></span>
                    </td>
                    <td class="rating-cell">
                        <span class="rating-pill"><span class="rating-stars">★★</span></span>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    <div class="mobile-cards"></div>
  </div>
`;
