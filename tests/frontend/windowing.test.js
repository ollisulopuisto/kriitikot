import { describe, it, expect, vi, afterEach } from 'vitest';
import { readFileSync } from 'node:fs';

let frame;
let fontDone;
let proximity;
function setup({ width = 1200, height = 200, full = false } = {}) {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: width });
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: height });
    Object.defineProperty(window, 'scrollY', { configurable: true, value: 0 });
    localStorage.removeItem('kriitikot_full_view');
    if (full !== null) localStorage.setItem('kriitikot_full_view', String(full));
    frame = null;
    proximity = null;
    vi.stubGlobal('IntersectionObserver', class { constructor(fn) { proximity = fn; } observe() {} });
    Object.defineProperty(document, 'fonts', { configurable: true, value: { ready: Promise.resolve(), addEventListener: (event, fn) => { if (event === 'loadingdone') fontDone = fn; } } });
    vi.stubGlobal('requestAnimationFrame', fn => { frame = fn; return 1; });
    const cell = i => `<td class="${i ? 'rating-cell' : 'movie-col'}"><button>${i}</button></td>`;
    document.body.innerHTML = `<div class="container"><input type="checkbox" id="windowing-toggle"><button id="load-more-button">More</button>
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
    it('starts full view on for an absent preference',()=>{
        setup({full:null});
        expect(window.reviewWindow.enabled).toBe(false);
        expect(document.getElementById('windowing-toggle').checked).toBe(true);
    });
    it('starts full view on when storage access throws',()=>{
        vi.spyOn(Storage.prototype, 'getItem').mockImplementation(()=>{throw new Error('blocked')});
        setup({full:null});
        expect(window.reviewWindow.enabled).toBe(false);
        expect(document.getElementById('windowing-toggle').checked).toBe(true);
    });
    it('starts full view on and persists an explicit desktop choice', () => {
        const {tick}=setup({full:true});
        expect(window.reviewWindow.enabled).toBe(false);
        expect(document.getElementById('windowing-toggle').checked).toBe(true);
        expect(document.querySelectorAll('tbody td')).toHaveLength(1600);
        document.getElementById('windowing-toggle').click();tick();
        expect(window.reviewWindow.enabled).toBe(true);
        expect(localStorage.getItem('kriitikot_full_view')).toBe('false');
    });
    it('remeasures after a late font load and parks with the new heights', () => {
        const { tick } = setup();
        const first = document.querySelector('tbody tr:not(.window-spacer)');
        expect(first.style.height).toBe('40px');
        first.getBoundingClientRect = () => ({top:-window.scrollY,bottom:80-window.scrollY,left:0,right:1600,width:1600,height:80});
        fontDone();
        tick();
        expect(first.style.height).toBe('80px');
        Object.defineProperty(window, 'scrollY', { configurable: true, value: 800 });
        window.dispatchEvent(new Event('scroll'));
        tick();
        expect(first.isConnected).toBe(false);
        expect(document.querySelector('tbody tr[data-index="20"]')).toBeTruthy();
        expect(document.querySelectorAll('tbody tr:not(.window-spacer)').length).toBeGreaterThan(0);
        const spacer = document.querySelector('tbody').firstElementChild;
        expect(spacer.classList.contains('window-spacer')).toBe(true);
        expect(spacer.style.height).toBe('80px');
        expect(spacer.firstElementChild.style.height).toBe('80px');
    });
    it('does not restore the full collection for scrolling keys on toolbar buttons', () => {
        setup();
        const button = document.getElementById('load-more-button');
        button.dispatchEvent(new KeyboardEvent('keydown', { key: 'PageDown', bubbles: true }));
        expect(document.querySelectorAll('.movie-card').length).toBe(0);
    });
    it('clears print coordinates then restores the same pinned header indices', () => {
        const { tick } = setup();
        const clone = document.createElement('table');
        clone.id = 'sticky-thead-clone';
        clone.appendChild(document.querySelector('table thead').cloneNode(true));
        document.body.appendChild(clone);
        const indices = () => Array.from(clone.tHead.rows[0].cells, cell => cell.getAttribute('aria-colindex'));
        const expected = Array.from({ length: 40 }, (_, i) => String(i + 1));
        expect(indices()).toEqual(expected);
        window.dispatchEvent(new Event('beforeprint'));
        expect(clone.querySelector('[aria-colindex], [aria-rowindex]')).toBeNull();
        window.dispatchEvent(new Event('afterprint'));
        tick();
        expect(document.getElementById('sticky-thead-clone')).toBe(clone);
        expect(indices()).toEqual(expected);
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
    it('keeps every loaded phone card connected without a toggle', () => {
        const { tick } = setup({ width: 390 });
        expect(document.querySelectorAll('tbody tr:not(.window-spacer)').length).toBe(40);
        expect(document.querySelectorAll('.movie-card').length).toBe(20);
        expect(document.querySelector('.window-spacer, .window-column-spacer')).toBeNull();
        document.getElementById('windowing-toggle').click();
        tick();
        expect(window.reviewWindow.enabled).toBe(false);
        expect(window.reviewWindow.retainedCount).toBe(0);
        const removed=document.querySelector('.movie-card');removed.remove();
        window.reviewWindow.prepare();tick();
        expect(removed.isConnected).toBe(false);
        expect(window.reviewWindow.retainedCount).toBe(0);
        expect(document.querySelector('[aria-rowcount], [aria-colcount], [aria-rowindex], [aria-colindex]')).toBeNull();
        expect(document.querySelectorAll('.movie-card').length).toBe(19);
        expect(document.querySelectorAll('tbody td').length).toBe(1600);
    });
    it('restores phone cards on resize and preserves the desktop choice', () => {
        const { tick } = setup();
        expect(window.reviewWindow.enabled).toBe(true);
        Object.defineProperty(window, 'innerWidth', {configurable:true,value:768});
        window.dispatchEvent(new Event('resize'));tick();
        expect(window.reviewWindow.enabled).toBe(false);
        expect(document.querySelectorAll('.movie-card')).toHaveLength(20);
        expect(window.reviewWindow.retainedCount).toBe(0);
        expect(document.querySelector('.window-spacer, .window-column-spacer')).toBeNull();
        Object.defineProperty(window, 'innerWidth', {configurable:true,value:769});
        window.dispatchEvent(new Event('resize'));tick();
        expect(window.reviewWindow.enabled).toBe(true);
        expect(document.querySelectorAll('.movie-card')).toHaveLength(0);
        document.getElementById('windowing-toggle').click();tick();
        expect(window.reviewWindow.enabled).toBe(false);
        for(const width of [390,1200]) {
            Object.defineProperty(window, 'innerWidth', {configurable:true,value:width});
            window.dispatchEvent(new Event('resize'));tick();
            expect(window.reviewWindow.enabled).toBe(false);
            expect(document.querySelectorAll('.movie-card')).toHaveLength(20);
        }
        expect(document.getElementById('windowing-toggle').checked).toBe(true);
    });

    it('preloads phone batches on downward scroll without windowing cards', () => {
        const { tick } = setup({width:390});
        const more=document.getElementById('load-more-button');
        Object.defineProperty(more,'offsetParent',{configurable:true,value:document.body});
        const click=vi.spyOn(more,'click');
        proximity([{isIntersecting:true}]);
        expect(click).not.toHaveBeenCalled();
        Object.defineProperty(window,'scrollY',{configurable:true,value:40});
        window.dispatchEvent(new Event('scroll'));tick();
        expect(click).toHaveBeenCalledTimes(1);
        expect(document.querySelectorAll('.movie-card')).toHaveLength(20);
        expect(window.reviewWindow.enabled).toBe(false);
        Object.defineProperty(window,'scrollY',{configurable:true,value:20});
        window.dispatchEvent(new Event('scroll'));tick();
        expect(click).toHaveBeenCalledTimes(1);
    });

});
