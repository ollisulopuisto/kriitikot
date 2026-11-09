import { describe, it, expect, beforeEach } from 'vitest';
import { setupDOM } from './test-helper';

/**
 * Regressio: kun yksi kriitikko oli valittu ja käyttäjä painoi "Lataa lisää",
 * valittu kriitikkosarake hyppäsi taulukon oikeaan reunaan. Syyt:
 *  1. täytesolu (.filler-column) lisättiin vain silloin näkyvillä oleviin
 *     riveihin, joten uudet ja myöhemmin näkyviin tulevat rivit jäivät ilman
 *  2. kiinteä sticky-otsikko on thead-klooni, joka rakennettiin hetkellä jolloin
 *     täytesarake oli poissa, ja täytesarakkeen mitattu px-leveys jäädytettiin
 *     kloonille, joten klooni venyi ja kriitikko hyppäsi oikealle
 */
const TABLE = `
  <div class="desktop-filters"></div>
  <div class="table-wrapper">
    <div id="review-container-desktop">
      <table>
        <thead>
          <tr class="critic-row">
            <th class="movie-col">Elokuva</th>
            <th class="rating-cell" data-critic-id="1" data-filtered="true"><div class="critic-name">Ensin</div></th>
          </tr>
        </thead>
        <tbody>
          <tr><td class="movie-col">A</td><td class="rating-cell"></td></tr>
          <tr style="display: none;"><td class="movie-col">B</td><td class="rating-cell"></td></tr>
        </tbody>
      </table>
    </div>
  </div>
  <div class="mobile-cards"></div>
`;

describe('Täytesarake ja Lataa lisää', () => {
  beforeEach(() => {
    window.innerWidth = 1400;
  });

  it('lisää täytesolun myös piilotettuihin riveihin', () => {
    const { window: win, document } = setupDOM(TABLE);
    win.removeFillerColumns();
    win.addFillerColumns();
    const rows = [...document.querySelectorAll('tbody tr')];
    expect(rows.length).toBe(2);
    rows.forEach((r) => expect(r.querySelectorAll(':scope > td.filler-column').length).toBe(1));
    expect(document.querySelectorAll('thead th.filler-column').length).toBe(1);
  });

  it('syncFillerCells täydentää "Lataa lisää" -rivit ilman duplikaatteja', () => {
    const { window: win, document } = setupDOM(TABLE);
    win.removeFillerColumns();
    win.addFillerColumns();
    // Simuloi loadMoreMovies: uusi rivi ilman täytesolua
    document.querySelector('tbody').insertAdjacentHTML(
      'beforeend',
      '<tr><td class="movie-col">C</td><td class="rating-cell"></td></tr>'
    );
    win.syncFillerCells();
    const rows = [...document.querySelectorAll('tbody tr')];
    expect(rows.length).toBe(3);
    rows.forEach((r) => expect(r.querySelectorAll(':scope > td.filler-column').length).toBe(1));
    expect(document.querySelectorAll('thead th.filler-column').length).toBe(1);
  });

  it('syncFillerCells ei lisää täytesaraketta jos sitä ei ole käytössä', () => {
    const { window: win, document } = setupDOM(TABLE);
    win.removeFillerColumns();
    win.syncFillerCells();
    expect(document.querySelectorAll('.filler-column').length).toBe(0);
  });

  it('sticky-otsikon klooni ei jäädytä täytesarakkeen leveyttä', () => {
    const { window: win, document } = setupDOM(TABLE);
    win.removeFillerColumns();
    win.addFillerColumns();
    const wrapper = document.querySelector('.table-wrapper');
    // jsdom ei tee layoutia: väärennä mitat jotta otsikko muuttuu kiinteäksi
    const rect = (top, bottom, width) => () => ({ top, bottom, left: 0, right: width, width, height: bottom - top });
    wrapper.getBoundingClientRect = rect(-200, 3000, 1300);
    document.querySelector('thead').getBoundingClientRect = rect(0, 40, 1300);
    document.querySelectorAll('thead th').forEach((th) => {
      th.getBoundingClientRect = th.classList.contains('filler-column') ? rect(0, 40, 10) : rect(0, 40, 120);
    });
    document.querySelector('.desktop-filters').getBoundingClientRect = rect(0, 100, 1300);
    win.dispatchEvent(new win.Event('resize'));
    const clone = document.getElementById('sticky-thead-clone');
    expect(clone).not.toBeNull();
    const filler = clone.querySelector('th.filler-column');
    expect(filler).not.toBeNull();
    expect(filler.style.width).toBe('auto');
    // varsinaiset sarakkeet säilyttävät mitatun leveyden
    expect(clone.querySelector('th.rating-cell').style.width).toBe('120px');
  });
});
