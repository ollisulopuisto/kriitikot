import {readFileSync} from 'node:fs';
import {it,expect} from 'vitest';
const code=readFileSync('static/ui.js','utf8');
it('keeps the other-group count in its own non-truncating element so a long query cannot clip it',()=>{
 document.body.innerHTML='<div class="mobile-filter collapsed"><div class="mobile-filter-bar"><button id="mobile-filter-toggle"><span class="toggle-text"></span><span class="toggle-count"></span></button><button class="mobile-filter-clear" hidden>x</button></div></div>';
 window.mobileFilterState=()=>({query:'a very long film title that will be truncated by ellipsis',criticId:'1',pubs:['HS'],minStars:1,minReviews:1});
 new Function('window','document',code+';initMobileFilterToggle();')(window,document);
 const text=document.querySelector('.toggle-text'),count=document.querySelector('.toggle-count');
 expect(text.textContent).toBe('Haku: a very long film title that will be truncated by ellipsis');
 expect(count.textContent).toBe(' · +2');
});
