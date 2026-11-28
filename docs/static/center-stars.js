/* Mobile decoration only: no click handlers and no change to review links. */
(function () {
    function initCenterStars(win = window, doc = document) {
        const root = doc.getElementById('review-container-mobile');
        if (!root) return () => {};
        const mobile = win.matchMedia('(max-width: 768px) and (hover: none) and (pointer: coarse)');
        const motion = win.matchMedia('(prefers-reduced-motion: no-preference)');
        const seen = new Set();
        let settle, clear, active, touching = false;
        const stop = () => { win.clearTimeout(settle); win.clearTimeout(clear); active?.classList.remove('center-star-active'); active = null; };
        const enabled = () => mobile.matches && motion.matches && !doc.hidden && !touching;
        function activate() {
            if (!enabled()) return;
            const center = win.innerHeight / 2;
            const candidates = [...root.querySelectorAll('.review-item')].filter(row => {
                const rect = row.getBoundingClientRect();
                return rect.height > 0 && rect.top >= 0 && rect.bottom <= win.innerHeight &&
                    Math.abs((rect.top + rect.bottom) / 2 - center) <= win.innerHeight * .15 &&
                    (typeof row.checkVisibility === 'function' ? row.checkVisibility({ checkVisibilityCSS: true }) : row.getClientRects().length > 0) && row.querySelector('.rating-pill');
            }).sort((a, b) => Math.abs((a.getBoundingClientRect().top + a.getBoundingClientRect().bottom) / 2 - center) - Math.abs((b.getBoundingClientRect().top + b.getBoundingClientRect().bottom) / 2 - center));
            const row = candidates[0];
            if (!row) return;
            const key = JSON.stringify([row.closest('.movie-card')?.dataset.movie, row.dataset.critic]);
            if (seen.has(key)) return;
            seen.add(key); active = row; row.classList.add('center-star-active');
            clear = win.setTimeout(() => { row.classList.remove('center-star-active'); if (active === row) active = null; }, 800);
        }
        function schedule() { stop(); if (enabled()) settle = win.setTimeout(activate, 200); }
        function down() { touching = true; stop(); }
        function up() { touching = false; schedule(); }
        win.addEventListener('scroll', schedule, { passive: true });
        win.addEventListener('resize', schedule);
        win.addEventListener('touchstart', down, { passive: true });
        win.addEventListener('touchend', up, { passive: true });
        win.addEventListener('touchcancel', up, { passive: true });
        doc.addEventListener('visibilitychange', schedule);
        mobile.addEventListener('change', schedule); motion.addEventListener('change', schedule);
        return () => {
            stop(); win.removeEventListener('scroll', schedule); win.removeEventListener('resize', schedule);
            win.removeEventListener('touchstart', down); win.removeEventListener('touchend', up); win.removeEventListener('touchcancel', up);
            doc.removeEventListener('visibilitychange', schedule); mobile.removeEventListener('change', schedule); motion.removeEventListener('change', schedule);
        };
    }
    window.initCenterStars = initCenterStars;
    document.addEventListener('DOMContentLoaded', () => initCenterStars());
})();
