import {readFileSync} from 'node:fs';
import {it,expect,vi} from 'vitest';
const code=readFileSync('static/ui.js','utf8');
it('summarizes active groups, keeps clear separate, and reads current state without owning it',()=>{
 document.body.innerHTML='<div class="mobile-filter collapsed"><div class="mobile-filter-bar"><button id="mobile-filter-toggle"><span class="toggle-text"></span></button><button class="mobile-filter-clear" aria-label="Tyhjennä kaikki hakuehdot" hidden>×</button></div></div>';
 let state={};window.mobileFilterState=()=>state;window.resetAllFilters=vi.fn(()=>state={});
 new Function('window','document',code+';initMobileFilterToggle();')(window,document);
 const toggle=document.querySelector('#mobile-filter-toggle'),clear=document.querySelector('.mobile-filter-clear'),label=document.querySelector('.toggle-text');
 expect(label.textContent).toBe('Hakuehdot');expect(clear.hidden).toBe(true);expect(toggle.contains(clear)).toBe(false);
 state={query:'pitkä elokuva',criticId:'1',pubs:['HS','IS'],minStars:3,minReviews:4,favoritesOn:true,chosenMovie:'Movie'};window.updateMobileFilterSummary();
 expect(label.textContent).toBe('Haku: pitkä elokuva · +6');expect(clear.hidden).toBe(false);expect(toggle.getAttribute('aria-label')).toContain('7 käytössä, haku: pitkä elokuva');
 toggle.click();expect(label.textContent).toBe('Piilota');expect(toggle.getAttribute('aria-expanded')).toBe('true');
 toggle.click();state={pubs:['HS','IS']};window.updateMobileFilterSummary();expect(label.textContent).toBe('Hakuehdot · 1');
 clear.click();expect(window.resetAllFilters).toHaveBeenCalledOnce();expect(label.textContent).toBe('Hakuehdot');expect(clear.hidden).toBe(true);expect(document.activeElement).toBe(toggle);expect(toggle.getAttribute('aria-expanded')).toBe('false');
});
