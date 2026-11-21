/* Connected-DOM windowing. Park original nodes, never clone interactive content.
 * Filters/sorts use prepare() to see the complete logical collection synchronously.
 * Scroll work only swaps the small viewport slice; no data fetch on this path.
 */
(() => {
    'use strict';
    const inRange = (start, end, low, high) => end >= low && start <= high;
    function margins(size, delta) {
        return delta < 0 ? [size * 1.5, size * 0.5] : [size * 0.5, size * 1.5];
    }
    window.reviewWindowMath = { inRange, margins };

    document.addEventListener('DOMContentLoaded', () => {
        const toggle = document.getElementById('windowing-toggle');
        const tbody = document.querySelector('#review-container-desktop tbody');
        const cards = document.querySelector('.mobile-cards');
        const wrapper = document.querySelector('.table-wrapper');
        const table = tbody?.closest('table');
        if (!toggle || !tbody || !cards || !wrapper || !table) return;
        let enabled = true;
        let printing = false;
        let suppressPreloadUntil = 0;
        let dirty = true;
        let scheduled = 0;
        let records = [];
        let columns = [];
        let previousY = window.scrollY;
        let previousX = wrapper.scrollLeft;
        const parkedCells = new Map();

        function restoreCells(row) {
            const saved = parkedCells.get(row);
            if (!saved) return;
            row.querySelectorAll(':scope > .window-column-spacer').forEach(n => n.remove());
            saved.cells.forEach((cell, index) => {
                if (row.children[index] !== cell) row.insertBefore(cell, row.children[index] || null);
            });
            row.style.height = saved.height;
            parkedCells.delete(row);
        }
        function restore() {
            for (const rec of records) {
                if (rec.spacer.isConnected) rec.spacer.replaceWith(rec.node);
                restoreCells(rec.node);
            }
        }
        function schedule() {
            if (!scheduled) scheduled = requestAnimationFrame(render);
        }
        function clearCoordinates() {
            const clone = document.getElementById('sticky-thead-clone');
            clone?.removeAttribute('aria-rowcount');
            clone?.removeAttribute('aria-colcount');
            clone?.querySelectorAll('[aria-rowindex], [aria-colindex]').forEach(node => { node.removeAttribute('aria-rowindex'); node.removeAttribute('aria-colindex'); });
            table.removeAttribute('aria-rowcount');
            table.removeAttribute('aria-colcount');
            table.querySelectorAll('[aria-rowindex], [aria-colindex]').forEach(node => {
                node.removeAttribute('aria-rowindex');
                node.removeAttribute('aria-colindex');
            });
        }
        function prepare() {
            suppressPreloadUntil = performance.now() + 200;
            restore();
            dirty = true;
            schedule();
        }
        function snapshot() {
            // This only runs after a mutation, never on an ordinary scroll frame.
            records = [
                ...Array.from(tbody.children).filter(n => n.tagName === 'TR'),
                ...cards.querySelectorAll(':scope > .movie-card')
            ].map((node, index) => {
                const desktop = node.tagName === 'TR';
                const rect = node.getBoundingClientRect();
                const style = getComputedStyle(node);
                const spacer = document.createElement(desktop ? 'tr' : 'div');
                spacer.className = 'window-spacer';
                spacer.setAttribute('aria-hidden', 'true');
                spacer.style.height = rect.height + 'px';
                if (style.display === 'none') spacer.style.display = 'none';
                spacer.style.marginTop = style.marginTop;
                spacer.style.marginBottom = style.marginBottom;
                if (desktop) {
                    const cell = spacer.insertCell();
                    cell.colSpan = Math.max(1, table.tHead?.rows[0]?.cells.length || 1);
                    cell.className = 'window-skeleton';
                    cell.style.height = rect.height + 'px';
                    node.setAttribute('aria-rowindex', String(index + 2));
                    Array.from(node.cells).forEach((cell, column) => cell.setAttribute('aria-colindex', String(column + 1)));
                }
                return { node, spacer, desktop, height: rect.height, visible: style.display !== 'none' };
            });
            const headers = Array.from(table.tHead?.rows[0]?.cells || []);
            columns = headers.map((node, index) => {
                const rect = node.getBoundingClientRect();
                node.setAttribute('aria-colindex', String(index + 1));
                return { node, index, width: rect.width };
            });
            // Print clears both headers. A pinned clone can survive afterprint,
            // so reindex it together with the original on every new snapshot.
            const pinned = document.getElementById('sticky-thead-clone');
            Array.from(pinned?.tHead?.rows[0]?.cells || []).forEach((cell, index) => {
                cell.setAttribute('aria-colindex', String(index + 1));
            });
            const visibleColumns = Math.max(1, columns.filter(c => c.width > 0).length);
            records.filter(r => r.desktop).forEach(r => { r.spacer.firstElementChild.colSpan = visibleColumns; });
            table.setAttribute('aria-rowcount', String(records.filter(r => r.desktop).length + 1));
            table.setAttribute('aria-colcount', String(headers.length));
            dirty = false;
        }
        function windowColumns(row, keep, columnKey, rowHeight) {
            if (row.contains(document.activeElement)) {
                restoreCells(row);
                return;
            }
            const old = parkedCells.get(row);
            if (old?.key === columnKey) return;
            restoreCells(row);
            const cells = Array.from(row.cells);
            if (cells.length !== columns.length || row.classList.contains('poster-row')) return;
            const fragment = document.createDocumentFragment();
            let gap = [];
            const flush = () => {
                if (!gap.length) return;
                const spacer = document.createElement('td');
                spacer.colSpan = Math.max(1, gap.filter(i => columns[i].width > 0).length);
                spacer.className = 'window-column-spacer window-skeleton';
                spacer.setAttribute('aria-hidden', 'true');
                // Hidden logical columns have zero width and must remain collapsed.
                if (gap.every(i => columns[i].width === 0)) spacer.style.display = 'none';
                fragment.appendChild(spacer);
                gap = [];
            };
            cells.forEach((cell, index) => {
                if (keep.has(index)) {
                    flush();
                    cell.setAttribute('aria-colindex', String(index + 1));
                    cell.classList.toggle('window-even-column', index % 2 === 1);
                    cell.classList.toggle('window-odd-column', index % 2 === 0);
                    fragment.appendChild(cell);
                } else gap.push(index);
            });
            flush();
            parkedCells.set(row, { cells, height: row.style.height, key: columnKey });
            row.style.height = rowHeight + 'px';
            row.replaceChildren(fragment);
        }
        function render() {
            scheduled = 0;
            if (!enabled || printing) {
                restore(); clearCoordinates();
                records = []; columns = []; parkedCells.clear();
                return;
            }
            if (dirty) snapshot();
            const desktop = window.innerWidth >= 769;
            const [before, after] = margins(window.innerHeight, window.scrollY - previousY);
            const [left, right] = margins(wrapper.clientWidth, wrapper.scrollLeft - previousX);
            const bounds = wrapper.getBoundingClientRect();
            const pinnedWidth = columns[0]?.width || 0;
            const keep = new Set([0]);
            for (const col of desktop ? columns : []) {
                const rect = col.node.getBoundingClientRect();
                if (col.width > 0 && inRange(rect.left, rect.right, bounds.left + pinnedWidth - left, bounds.right + right)) keep.add(col.index);
                if (col.node.contains(document.activeElement)) keep.add(col.index);
            }
            const columnKey = Array.from(keep).join(',');
            // Read positions first, then perform all DOM swaps.
            const visible = records.map(rec => {
                if (rec.node.contains(document.activeElement)) return true;
                if (rec.desktop !== desktop || !rec.visible) return false;
                const anchor = rec.spacer.isConnected ? rec.spacer : rec.node;
                const rect = anchor.getBoundingClientRect();
                return inRange(rect.top, rect.bottom, -before, window.innerHeight + after);
            });
            records.forEach((rec, i) => {
                if (visible[i]) {
                    if (rec.spacer.isConnected) rec.spacer.replaceWith(rec.node);
                    if (desktop && rec.desktop) windowColumns(rec.node, keep, columnKey, rec.height);
                } else if (rec.node.isConnected) {
                    rec.node.replaceWith(rec.spacer);
                }
            });
            previousY = window.scrollY;
            previousX = wrapper.scrollLeft;
        }
        window.reviewWindow = { prepare, schedule, restore, get enabled() { return enabled; }, get retainedCount() { return records.length + parkedCells.size; } };
        // Capture before the legacy handlers read a complete DOM collection.
        for (const event of ['click', 'input', 'change', 'keydown']) {
            document.addEventListener(event, e => {
                if (!e.target.closest?.('.container, #sticky-thead-wrapper')) return;
                const scrollingKey = event === 'keydown' && ['PageDown', 'PageUp', 'Home', 'End', 'ArrowDown', 'ArrowUp'].includes(e.key);
                const editable = e.target.closest?.('input, select, textarea, [contenteditable="true"], [role="slider"]');
                if (scrollingKey && !editable) return;
                prepare();
            }, true);
        }
        document.addEventListener('focusin', schedule);
        document.addEventListener('focusout', schedule);
        document.addEventListener('table-sorted', () => { dirty = true; schedule(); });
        window.addEventListener('scroll', schedule, { passive: true });
        wrapper.addEventListener('scroll', schedule, { passive: true });
        window.addEventListener('resize', prepare);
        document.fonts?.ready.then(prepare);
        document.fonts?.addEventListener('loadingdone', prepare);
        window.addEventListener('beforeprint', () => { printing = true; restore(); clearCoordinates(); });
        window.addEventListener('afterprint', () => { printing = false; prepare(); });
        // Preload the next logical batch before the user reaches the boundary.
        // The manual button remains the fallback when IntersectionObserver is absent.
        const more = document.getElementById('load-more-button');
        let moreInRange = false;
        let preloadY = window.scrollY;
        let pendingDownY = null;
        function attemptPreload() {
            if (enabled && !printing && !dirty && performance.now() >= suppressPreloadUntil &&
                pendingDownY === window.scrollY && moreInRange && more.offsetParent !== null && !more.disabled) {
                pendingDownY = null;
                more.click();
            }
        }
        function maybePreload() {
            const y = window.scrollY;
            pendingDownY = y > preloadY && !dirty && performance.now() >= suppressPreloadUntil ? y : null;
            preloadY = y;
            attemptPreload();
        }
        const preload = typeof IntersectionObserver === 'function' && more
            ? new IntersectionObserver(entries => {
                moreInRange = entries.some(e => e.isIntersecting);
                // A jump can emit scroll before proximity is delivered. Retain
                // only the latest downward movement, never an old/upward intent.
                attemptPreload();
            }, { rootMargin: '150% 0px' }) : null;
        if (preload) {
            preload.observe(more);
            window.addEventListener('scroll', maybePreload, { passive: true });
        }
        toggle.addEventListener('click', () => {
            enabled = !enabled;
            toggle.setAttribute('aria-pressed', String(!enabled));
            toggle.textContent = enabled ? 'Näytä koko näkymä' : 'Käytä kevyttä näkymää';
            prepare();
        });
        schedule();
    }, { once: true });
})();
