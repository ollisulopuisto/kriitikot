import {readFileSync} from 'node:fs';import {it,expect,vi,afterEach} from 'vitest';
const code=readFileSync('static/center-stars.js','utf8');
afterEach(()=>{vi.useRealTimers();});
it('works where Element.checkVisibility is unavailable (older Safari)',()=>{
 vi.useFakeTimers();document.body.innerHTML='<div id="review-container-mobile"><div class="movie-card" data-movie="M"><div class="review-item" data-critic="1"><a class="rating-pill">s</a></div></div></div>';
 const row=document.querySelector('.review-item');row.getBoundingClientRect=()=>({top:350,bottom:450,height:100});row.getClientRects=()=>[{}];delete row.checkVisibility;
 window.innerHeight=800;window.matchMedia=()=>({matches:true,addEventListener(){},removeEventListener(){}});window.eval(code);window.initCenterStars();
 const errors=[];window.addEventListener('error',e=>{errors.push(e.message);e.preventDefault();});
 window.dispatchEvent(new Event('scroll'));
 let threw=null;try{vi.advanceTimersByTime(200);}catch(e){threw=e;}
 expect(threw).toBeNull();expect(errors).toEqual([]);expect(row.classList.contains('center-star-active')).toBe(true);
});
