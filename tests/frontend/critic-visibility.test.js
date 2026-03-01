import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setupDOM, minimalHTML } from './test-helper';

describe('Kriitikkosarakkeiden näkyvyys', () => {
  let dom;

  beforeEach(() => {
    dom = setupDOM(minimalHTML);
    // Globaalit muuttujat alustetaan scripts/app.js:ssä
  });

  it('Pitäisi piilottaa kriitikon sarake, jos hänellä ei ole yhtään kriteerin täyttävää arviota näkyvillä riveillä', () => {
    const { document, window } = dom;
    
    // Alustila: molemmat kriitikot näkyvissä
    const bonoHeader = document.querySelector('th[data-critic-id="1"]');
    const toinenHeader = document.querySelector('th[data-critic-id="2"]');
    
    expect(bonoHeader.classList.contains('filter-hidden')).toBe(false);
    expect(toinenHeader.classList.contains('filter-hidden')).toBe(false);

    // Asetetaan tähtisuodatin 5 tähden kohdalle
    // filterByStars(5) pitäisi jättää vain "Huippu Elokuva" näkyviin.
    // "Toinen Kriitikko" on antanut sille 2 tähteä, joten hänen sarakkeensa pitäisi piiloutua.
    
    if (typeof window.filterByStars === 'function') {
      const starSlider = document.getElementById('star-filter-slider');
      if (starSlider) starSlider.value = 5;
      window.filterByStars(5);
    } else {
      throw new Error('filterByStars not found in window');
    }

    // Tarkistetaan rivien näkyvyys
    const rows = document.querySelectorAll('tbody tr');
    expect(rows[0].style.display).not.toBe('none'); // Huippu Elokuva
    expect(rows[1].style.display).toBe('none');     // Huono Elokuva

    // Tarkistetaan sarakkeiden näkyvyys
    // Susanna Bono (5 tähteä) - pitäisi olla näkyvissä
    expect(bonoHeader.classList.contains('filter-hidden')).toBe(false);
    
    // Toinen Kriitikko (2 tähteä) - pitäisi olla piilossa, koska 2 < 5
    expect(toinenHeader.classList.contains('filter-hidden')).toBe(true);
  });
});
