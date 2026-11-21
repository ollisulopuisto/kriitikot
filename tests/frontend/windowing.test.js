import { describe, it, expect, vi, afterEach } from 'vitest';
import { readFileSync } from 'node:fs';

let frame;
let fontDone;
function setup({ width = 1200, height = 200 } = {}) {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: width });
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: height });
    Object.defineProperty(window, 'scrollY', { configurable: true, value: 0 });
    frame = null;
    Object.defineProperty(document, 'fonts', { configurable: true, value: { ready: Promise.resolve(), addEventListener: (event, fn) => { if (event === 'loadingdone') fontDone = fn; } } });
    vi.stubGlobal('requestAnimationFrame', fn => { frame = fn; return 1; });
    const cell = i => `<td class="${i ? 'rating-cell' : 'movie-col'}"><button>${i}</button></td>`;
    document.body.innerHTML = `<div class="container"><button id="windowing-toggle"></button>
      <div id="review-container-desktop"><div class="table-wrapper"><table><thead><tr>
      ${Array.from({ length: 40 }, (_, i) => `<th>${i}</th>`).join('')}</tr></thead><tbody>
      ${Array.from({ length: 40 }, (_, i) => `<tr data-index="${i}">${Array.from({ length: 40 }, (_, j) => cell(j)).join('')}</tr>`).join('')}
      </tbody></table></div></div><div class="mobile-cards">
      ${Array.from({ length: 20 }, (_, i) => `<div class="movie-card" data-index="${i}"><button>card</button></div>`).join('')}</div></div>`;
    const box = (top, left, w, h) => ({ top, left, width: w, height: h, right: left + w, bottom: top + h });
    const wrapper = document.querySelector('.table-wrapper');
    Object.defineProperty(wrapper, 'clientWidth', { value: 200 });
    wrapper.getBoundingClientRect = () => box(0, 0, 200, 200);
    document.querySelectorAll('th').forEach((n, i) => { n.getBoundingClientRect = () => box(0, i * 40, 40, 40); });
    document.querySelectorAll('tbody tr, .movie-card').forEach(n => {
        const i = Number(n.dataset.index);
        n.getBoundingClientRect = () => box(i * 40 - window.scrollY, 0, 1600, 40);
    });
    // Spacers have the same geometry as the nodes they replace.
    const original = Element.prototype.getBoundingClientRect;
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function () {
        if (this.classList.contains('window-spacer')) {
            const siblings = Array.from(this.parentElement.children);
            return box(siblings.indexOf(this) * 40 - window.scrollY, 0, 1600, 40);
        }
        return original.call(this);
    });
    new Function(readFileSync('static/windowing.js', 'utf8'))();
    document.dispatchEvent(new Event('DOMContentLoaded'));
    const tick = () => { const fn = frame; frame = null; fn?.(); };
    tick();
    return { tick, wrapper };
}

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('review viewport window', () => {
    it('remeasures after a late font load and parks with the new heights', () => {
        const { tick } = setup();
        window.reviewWindow.prepare();
        const first = document.querySelector('tbody tr');
        first.getBoundingClientRect = () => ({top:0,bottom:80,left:0,right:1600,width:1600,height:80});
        fontDone();
        tick();
        expect(first.style.height).toBe('80px');
    });
    it('does not restore the full collection for scrolling keys on toolbar buttons', () => {
        setup();
        const button = document.getElementById('windowing-toggle');
        button.dispatchEvent(new KeyboardEvent('keydown', { key: 'PageDown', bubbles: true }));
        expect(document.querySelectorAll('.movie-card').length).toBe(0);
    });
    it('biases preload toward the direction of travel', () => {
        setup();
        expect(window.reviewWindowMath.margins(200, 1)).toEqual([100, 300]);
        expect(window.reviewWindowMath.margins(200, -1)).toEqual([300, 100]);
    });
    it('parks both offscreen rows and critic cells, retaining original nodes', () => {
        const { tick } = setup();
        expect(document.querySelectorAll('tbody tr:not(.window-spacer)').length).toBeLessThan(20);
        expect(document.querySelectorAll('tbody td').length).toBeLessThan(700);
        expect(document.querySelectorAll('.movie-card').length).toBe(0);
        window.reviewWindow.prepare();
        expect(document.querySelectorAll('tbody tr').length).toBe(40);
        expect(document.querySelectorAll('tbody td').length).toBe(1600);
        expect(document.querySelectorAll('.movie-card').length).toBe(20);
        const original = document.querySelector('tbody tr');
        tick();
        window.reviewWindow.prepare();
        expect(document.querySelector('tbody tr')).toBe(original);
    });
    it('does not steal keyboard focus while restoring partially parked columns', () => {
        setup();
        const button = document.querySelector('tbody button');
        button.focus();
        window.reviewWindow.prepare();
        expect(document.activeElement).toBe(button);
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }));
        expect(document.activeElement).toBe(button);
    });
    it('only windows vertically on phones and offers a complete-view fallback', () => {
        const { tick } = setup({ width: 390 });
        expect(document.querySelectorAll('tbody tr:not(.window-spacer)').length).toBe(0);
        expect(document.querySelectorAll('.movie-card').length).toBeLessThan(20);
        document.getElementById('windowing-toggle').click();
        tick();
        expect(window.reviewWindow.enabled).toBe(false);
        expect(document.querySelector('[aria-rowcount], [aria-colcount], [aria-rowindex], [aria-colindex]')).toBeNull();
        expect(document.querySelectorAll('.movie-card').length).toBe(20);
        expect(document.querySelectorAll('tbody td').length).toBe(1600);
    });
});
